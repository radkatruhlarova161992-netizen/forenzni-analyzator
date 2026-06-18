"""Jednotné dohledání firmy podle IČO přes více veřejných zdrojů."""

from dataclasses import asdict, dataclass, field
from html import unescape
import re
from typing import Any

import requests

from core.config import (
    ARES_URL,
    HEADERS,
    HLIDAC_SUBJEKT_URL,
    JUSTICE_REJSTRIK_SEARCH_URL,
    JUSTICE_VYPIS_URL,
    KURZY_COMPANY_URL,
    PENIZE_REJSTRIK_SEARCH_URL,
    REQUEST_TIMEOUT,
)
from core.utils import clean_ico, format_kurzy_search_link
from sources.detail import fetch_detail_company_lookup
from sources.hlidac import fetch_hlidac_company_lookup
from sources.penize import fetch_penize_company_lookup


@dataclass(slots=True)
class SourceAttempt:
    source_name: str
    source_url: str
    status: str
    error: str | None = None


@dataclass(slots=True)
class CompanyLookupResult:
    status: str
    ico: str
    nazev: str | None = None
    sidlo: str | None = None
    stav: str | None = None
    source_name: str | None = None
    source_url: str | None = None
    confidence: str | None = None
    attempts: list[SourceAttempt] = field(default_factory=list)
    manual_verification_urls: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["attempts"] = [asdict(attempt) for attempt in self.attempts]
        return data


def _manual_urls(ico: str) -> dict[str, str]:
    return {
        "ARES": ARES_URL.format(ico=ico),
        "Justice": JUSTICE_VYPIS_URL.format(ico=ico),
        "Hlídač státu": HLIDAC_SUBJEKT_URL.format(ico=ico),
        "Kurzy.cz": format_kurzy_search_link(ico, True),
    }


def _append_attempt(
    attempts: list[SourceAttempt],
    source_name: str,
    source_url: str,
    status: str,
    error: str | None = None,
) -> None:
    attempts.append(
        SourceAttempt(
            source_name=source_name,
            source_url=source_url,
            status=status,
            error=error,
        )
    )


def _lookup_ares(ico: str) -> dict[str, Any]:
    source_url = ARES_URL.format(ico=ico)
    result: dict[str, Any] = {
        "status": "not_found",
        "ico": ico,
        "nazev": None,
        "sidlo": None,
        "stav": None,
        "source_name": "ARES",
        "source_url": source_url,
        "confidence": "high",
        "error": None,
    }
    try:
        response = requests.get(source_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        if response.status_code == 404:
            return result
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise ValueError("Odpověď ARES není JSON objekt.")

        company_name = data.get("obchodniJmeno")
        if not company_name:
            return result

        sidlo = data.get("sidlo", {}) or {}
        address = sidlo.get("textovaAdresa")
        if not address:
            address_parts = [
                sidlo.get("nazevUlice") or sidlo.get("nazevCastiObce"),
                sidlo.get("cisloDomovni") and str(sidlo.get("cisloDomovni")),
                sidlo.get("nazevObce"),
                sidlo.get("psc") and str(sidlo.get("psc")),
            ]
            address = ", ".join(part for part in address_parts if part)

        full_text_check = str(data).lower()
        in_liquidation = "likvidace" in full_text_check or "v likvidaci" in str(company_name).lower()
        if data.get("datumZaniku"):
            status = "Zaniklý subjekt"
        else:
            status = "V likvidaci" if in_liquidation else "Aktivní"

        result.update(
            {
                "status": "found",
                "nazev": company_name,
                "sidlo": address,
                "stav": status,
            }
        )
    except requests.exceptions.Timeout:
        result["status"] = "failed"
        result["error"] = "ARES neodpovědělo včas."
    except requests.exceptions.RequestException as exc:
        result["status"] = "failed"
        result["error"] = f"Chyba spojení s ARES: {exc}"
    except ValueError as exc:
        result["status"] = "failed"
        result["error"] = f"Nelze zpracovat odpověď ARES: {exc}"

    return result


def _lookup_justice(ico: str) -> dict[str, Any]:
    source_url = JUSTICE_REJSTRIK_SEARCH_URL.format(ico=ico)
    result: dict[str, Any] = {
        "status": "not_found",
        "ico": ico,
        "nazev": None,
        "sidlo": None,
        "stav": None,
        "source_name": "Justice / veřejný rejstřík",
        "source_url": source_url,
        "confidence": "high",
        "error": None,
    }
    try:
        response = requests.get(source_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        text = response.text
        if ico not in text:
            return result

        # Current public Justice search page echoes the requested ICO in the form,
        # but without a reliably parseable exact result in static HTML we do not
        # treat it as a found entity.
    except requests.exceptions.Timeout:
        result["status"] = "failed"
        result["error"] = "Justice neodpovědělo včas."
    except requests.exceptions.RequestException as exc:
        result["status"] = "failed"
        result["error"] = f"Chyba spojení s Justice: {exc}"

    return result


def _lookup_kurzy(ico: str) -> dict[str, Any]:
    source_url = KURZY_COMPANY_URL.format(ico=ico)
    result: dict[str, Any] = {
        "status": "not_found",
        "ico": ico,
        "nazev": None,
        "sidlo": None,
        "stav": None,
        "source_name": "Kurzy.cz",
        "source_url": source_url,
        "confidence": "low",
        "error": None,
    }
    try:
        response = requests.get(source_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        text = response.text
        if "Ověření uživatele" in text:
            result["status"] = "partial"
            return result
        if ico in text:
            title_match = re.search(r"<title>(.*?)</title>", text, re.I | re.S)
            if title_match:
                title = unescape(title_match.group(1)).strip()
                if title and "Kurzy.cz" not in title:
                    result["status"] = "found"
                    result["nazev"] = title
                    return result
            result["status"] = "partial"
    except requests.exceptions.Timeout:
        result["status"] = "failed"
        result["error"] = "Kurzy.cz neodpovědělo včas."
    except requests.exceptions.RequestException as exc:
        result["status"] = "failed"
        result["error"] = f"Chyba spojení s Kurzy.cz: {exc}"
    return result


def find_company_by_ico(ico: str) -> CompanyLookupResult:
    ico = clean_ico(ico)
    attempts: list[SourceAttempt] = []
    manual_urls = _manual_urls(ico)

    if not ico:
        return CompanyLookupResult(
            status="not_found",
            ico="",
            attempts=attempts,
            manual_verification_urls=manual_urls,
        )

    source_functions = [
        _lookup_ares,
        _lookup_justice,
        fetch_hlidac_company_lookup,
        _lookup_kurzy,
        fetch_penize_company_lookup,
        fetch_detail_company_lookup,
    ]

    for source_function in source_functions:
        lookup = source_function(ico)
        _append_attempt(
            attempts,
            source_name=lookup["source_name"],
            source_url=lookup["source_url"],
            status=lookup["status"],
            error=lookup.get("error"),
        )
        if lookup["status"] == "found":
            return CompanyLookupResult(
                status="found",
                ico=ico,
                nazev=lookup.get("nazev"),
                sidlo=lookup.get("sidlo"),
                stav=lookup.get("stav"),
                source_name=lookup["source_name"],
                source_url=lookup["source_url"],
                confidence=lookup["confidence"],
                attempts=attempts,
                manual_verification_urls=manual_urls,
            )

    return CompanyLookupResult(
        status="not_found",
        ico=ico,
        attempts=attempts,
        manual_verification_urls=manual_urls,
    )
