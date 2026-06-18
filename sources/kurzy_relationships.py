"""Rozsirene vztahy z Kurzy.cz."""

from __future__ import annotations

from html import unescape
import re
from typing import Any
from urllib.parse import urljoin

import requests

from core.config import HEADERS, KURZY_COMPANY_URL, REQUEST_TIMEOUT
from core.utils import clean_ico
from models.relationship_record import RelationshipRecord

KURZY_SOURCE_NAME = "Kurzy.cz"


def _strip_tags(value: str) -> str:
    return " ".join(unescape(re.sub(r"<[^>]+>", " ", str(value or ""))).split())


def _normalize_key(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def _extract_address(segment: str) -> str | None:
    match = re.search(
        r"([A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽa-záčďéěíňóřšťúůýž0-9.,/\- ]+\d{3}\s?\d{2}[A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽa-záčďéěíňóřšťúůýž0-9.,/\- ]*)",
        segment,
    )
    if not match:
        return None
    address = " ".join(match.group(1).split())
    return address if len(address) > 8 else None


def _extract_status(segment: str) -> str | None:
    lowered = _normalize_key(segment)
    if "v likvidaci" in lowered or "likvidace" in lowered:
        return "V likvidaci"
    if "vymaz" in lowered or "zanikl" in lowered or "zanik" in lowered:
        return "Historická"
    if "aktiv" in lowered:
        return "Aktuální"
    return None


def _detect_relationship_type(segment: str) -> str:
    lowered = _normalize_key(segment)
    keyword_map = [
        ("jednatel", "jednatel"),
        ("společník", "společník"),
        ("spolecnik", "společník"),
        ("vlastník", "vlastník"),
        ("vlastnik", "vlastník"),
        ("akcionář", "akcionář"),
        ("akcionar", "akcionář"),
        ("statutár", "statutární orgán"),
        ("statutar", "statutární orgán"),
        ("prokur", "prokura"),
        ("adresa", "společná adresa"),
        ("sídl", "společná adresa"),
        ("sidl", "společná adresa"),
        ("fúz", "fúze"),
        ("fuz", "fúze"),
        ("nástup", "nástupnictví"),
        ("nastup", "nástupnictví"),
        ("likvid", "likvidace"),
        ("výmaz", "výmaz"),
        ("vymaz", "výmaz"),
        ("zanik", "výmaz"),
    ]
    for keyword, label in keyword_map:
        if keyword in lowered:
            return label
    return "vazba z veřejného agregátoru"


def _detect_entity_type(name: str, relationship_type: str | None) -> str:
    lowered_name = _normalize_key(name)
    if relationship_type == "společná adresa":
        return "address"
    company_markers = (
        "s.r.o",
        "s. r. o",
        "a.s",
        "a. s",
        "v.o.s",
        "k.s",
        "z.s",
        "družstvo",
        "spol.",
        "holding",
        "invest",
    )
    if any(marker in lowered_name for marker in company_markers):
        return "company"
    if len(name.split()) >= 2:
        return "person"
    return "unknown"


def _find_relationship_page_url(company_html: str, fallback_url: str) -> str:
    canonical_match = re.search(
        r'<link[^>]+rel="canonical"[^>]+href="(?P<href>[^"]+)"',
        company_html,
        re.I,
    )
    if canonical_match:
        canonical_url = canonical_match.group("href")
        if "/vztahy/" in canonical_url:
            return canonical_url
        return urljoin(canonical_url.rstrip("/") + "/", "vztahy/")

    patterns = [
        r'href="(?P<href>[^"]+/vztahy/[^"]*)"',
        r'href="(?P<href>[^"]*vztahy/)"',
    ]
    for pattern in patterns:
        match = re.search(pattern, company_html, re.I)
        if match:
            return urljoin(fallback_url, match.group("href"))
    return urljoin(fallback_url, "vztahy/")


def _extract_ico_from_href_or_snippet(href: str, snippet: str) -> str | None:
    patterns = [
        r"/(?P<ico>\d{8})/",
        r"/ico/(?P<ico>\d{8})/",
        r"IČO[:\s]*(?P<ico>\d{3}\s?\d{2}\s?\d{3})",
        r"ICO[:\s]*(?P<ico>\d{3}\s?\d{2}\s?\d{3})",
    ]
    for pattern in patterns:
        match = re.search(pattern, f"{href} {snippet}", re.I)
        if match:
            ico = clean_ico(match.group("ico"))
            return ico if len(ico) == 8 else None
    return None


def _looks_like_captcha_or_loader(html: str) -> bool:
    lowered = html.lower()
    markers = ("id=\"loading\"", "loadingb.gif", "captcha", "window.settimeout")
    return any(marker in lowered for marker in markers)


def _dedupe_records(records: list[RelationshipRecord]) -> tuple[list[RelationshipRecord], int]:
    deduped: list[RelationshipRecord] = []
    seen: set[tuple[str, ...]] = set()
    skipped = 0
    for record in records:
        if record.target_ico:
            signature = ("ico", record.target_ico)
        else:
            signature = (
                "name_address",
                _normalize_key(record.target_entity_name),
                _normalize_key(record.target_address),
            )
        if signature in seen:
            skipped += 1
            continue
        seen.add(signature)
        deduped.append(record)
    return deduped, skipped


def parse_kurzy_relationships(html: str, source_url: str) -> list[dict[str, Any]]:
    """Vytahne vztahy ze stranky Kurzy bez domysleni chybejicich IČO."""
    records: list[RelationshipRecord] = []
    if not html:
        return []
    if _looks_like_captcha_or_loader(html):
        return []

    anchor_pattern = re.compile(
        r'<a[^>]+href="(?P<href>[^"]+)"[^>]*>(?P<label>.*?)</a>',
        re.I | re.S,
    )
    for match in anchor_pattern.finditer(html):
        href = match.group("href")
        label = _strip_tags(match.group("label"))
        if not label or len(label) < 3:
            continue
        if label.lower() in {"obchodní rejstřík", "kurzy.cz", "firmy", "rejstřík firem"}:
            continue
        if any(skip in href for skip in ("/kontakt/", "/mail/", "/telefon/", "#")):
            continue

        snippet_start = max(0, match.start() - 420)
        snippet_end = min(len(html), match.end() + 420)
        raw_snippet = html[snippet_start:snippet_end]
        snippet = _strip_tags(raw_snippet)
        if len(snippet) < 8:
            continue

        related_ico = _extract_ico_from_href_or_snippet(href, snippet)
        relationship_type = _detect_relationship_type(snippet)
        entity_type = _detect_entity_type(label, relationship_type)
        if entity_type == "unknown" and not related_ico:
            continue

        status = _extract_status(snippet)
        is_historical = bool(status == "Historická" or relationship_type in {"výmaz", "fúze"})
        record = RelationshipRecord(
            source_entity_name=None,
            source_ico=None,
            target_entity_name=label,
            target_ico=related_ico,
            target_address=_extract_address(snippet),
            target_type=entity_type,
            relationship_type=relationship_type,
            relationship_direction="unknown",
            is_historical=is_historical,
            is_current=not is_historical,
            source_name=KURZY_SOURCE_NAME,
            source_url=source_url,
            confidence="medium",
            verification_status="unverified_external",
            raw_evidence=snippet[:600],
            warnings=["Vazba pochází z veřejného agregátoru a je nutné ji ručně ověřit."],
        )
        records.append(record)

    deduped, _ = _dedupe_records(records)
    return [record.to_legacy_dict() for record in deduped]


def fetch_kurzy_relationships(ico: str) -> dict[str, Any]:
    company_url = KURZY_COMPANY_URL.format(ico=ico)
    result: dict[str, Any] = {
        "status": "not_found",
        "source_name": KURZY_SOURCE_NAME,
        "source_url": company_url,
        "relationship_page_url": None,
        "relationships": [],
        "diagnostics": {
            "kurzy_total_raw": 0,
            "kurzy_total_deduped": 0,
            "kurzy_skipped_duplicates": 0,
            "kurzy_without_ico": 0,
            "parser_warnings": [],
        },
        "warnings": [],
        "raw_snippet": None,
        "error": None,
    }
    try:
        company_response = requests.get(company_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        company_response.raise_for_status()
        relationship_url = _find_relationship_page_url(company_response.text, company_url)
        result["relationship_page_url"] = relationship_url
        result["source_url"] = relationship_url

        relationship_response = requests.get(
            relationship_url,
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
        )
        relationship_response.raise_for_status()
        html = relationship_response.text
        result["raw_snippet"] = _strip_tags(html[:1200])

        parser_warnings: list[str] = []
        if _looks_like_captcha_or_loader(html):
            parser_warnings.append(
                "Kurzy.cz vrátilo mezistránku nebo ochrannou stránku. Vazby je nutné ověřit ručně."
            )

        raw_rows = parse_kurzy_relationships(html, relationship_url)
        deduped_rows, skipped = _dedupe_legacy_relationships(raw_rows)
        without_ico = len([row for row in deduped_rows if not row.get("ico")])
        result["relationships"] = deduped_rows
        result["diagnostics"] = {
            "kurzy_total_raw": len(raw_rows),
            "kurzy_total_deduped": len(deduped_rows),
            "kurzy_skipped_duplicates": skipped,
            "kurzy_without_ico": without_ico,
            "parser_warnings": parser_warnings,
        }
        result["warnings"] = parser_warnings
        result["status"] = "found" if deduped_rows else "not_found"
    except requests.exceptions.Timeout:
        result["status"] = "failed"
        result["error"] = "Kurzy.cz neodpovědělo včas."
    except requests.exceptions.RequestException as exc:
        result["status"] = "failed"
        result["error"] = f"Chyba spojení s Kurzy.cz: {exc}"
    except ValueError as exc:
        result["status"] = "failed"
        result["error"] = f"Nevalidní odpověď Kurzy.cz: {exc}"

    return result


def _dedupe_legacy_relationships(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, ...]] = set()
    skipped = 0
    for row in rows:
        if row.get("ico"):
            signature = ("ico", str(row["ico"]))
        else:
            signature = (
                "name_address",
                _normalize_key(row.get("firma") or row.get("nazev")),
                _normalize_key(row.get("adresa")),
            )
        if signature in seen:
            skipped += 1
            continue
        seen.add(signature)
        deduped.append(row)
    return deduped, skipped
