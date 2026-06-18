"""Rozsirene vztahy z Kurzy.cz."""

from __future__ import annotations

from html import unescape
import re
from typing import Any
from urllib.parse import urljoin

import requests

from core.config import HEADERS, KURZY_COMPANY_URL, REQUEST_TIMEOUT
from core.utils import clean_ico

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


def _detect_relationship_type(segment: str) -> str | None:
    lowered = _normalize_key(segment)
    keyword_map = [
        ("jednatel", "jednatel"),
        ("společník", "společník"),
        ("vlastník", "vlastník"),
        ("akcionář", "akcionář"),
        ("statutár", "statutární orgán"),
        ("prokur", "prokura"),
        ("adresa", "společná adresa"),
        ("sídl", "společná adresa"),
        ("fúz", "fúze"),
        ("nástup", "nástupnictví"),
        ("likvid", "likvidace"),
        ("výmaz", "výmaz"),
        ("zanik", "výmaz"),
    ]
    for keyword, label in keyword_map:
        if keyword in lowered:
            return label
    return None


def _detect_entity_type(name: str, relationship_type: str | None) -> str:
    lowered_name = _normalize_key(name)
    if relationship_type == "společná adresa":
        return "address"
    company_markers = ("s.r.o", "a.s", "v.o.s", "k.s", "z.s", "zapsaný spolek", "spol.")
    if any(marker in lowered_name for marker in company_markers):
        return "company"
    if len(name.split()) >= 2:
        return "person"
    return "unknown"


def _find_relationship_page_url(company_html: str, fallback_url: str) -> str:
    patterns = [
        r'href="(?P<href>[^"]+/vztahy/[^"]*)"',
        r'href="(?P<href>[^"]*vztahy/)"',
    ]
    for pattern in patterns:
        match = re.search(pattern, company_html, re.I)
        if match:
            return urljoin(fallback_url, match.group("href"))
    return urljoin(fallback_url, "vztahy/")


def _dedupe_relationships(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, ...]] = set()
    skipped = 0
    for row in rows:
        if row.get("ico"):
            signature = ("ico", str(row["ico"]))
        else:
            signature = (
                "name_address",
                _normalize_key(row.get("nazev")),
                _normalize_key(row.get("adresa")),
            )
        if signature in seen:
            skipped += 1
            continue
        seen.add(signature)
        deduped.append(row)
    return deduped, skipped


def fetch_kurzy_relationships(ico: str) -> dict[str, Any]:
    company_url = KURZY_COMPANY_URL.format(ico=ico)
    result: dict[str, Any] = {
        "status": "nenalezeno",
        "source_name": KURZY_SOURCE_NAME,
        "source_url": company_url,
        "relationship_page_url": None,
        "relationships": [],
        "diagnostics": {
            "kurzy_total_raw": 0,
            "kurzy_total_deduped": 0,
            "kurzy_skipped_duplicates": 0,
        },
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

        raw_rows: list[dict[str, Any]] = []
        anchor_pattern = re.compile(
            r'<a[^>]+href="(?P<href>[^"]+)"[^>]*>(?P<label>.*?)</a>',
            re.I | re.S,
        )
        for match in anchor_pattern.finditer(html):
            href = match.group("href")
            label = _strip_tags(match.group("label"))
            if not label or len(label) < 3:
                continue
            if any(skip in href for skip in ("/kontakt/", "/mail/", "/telefon/")):
                continue

            related_ico_match = re.search(r"/ico/(?P<ico>\d{8})/", href)
            related_ico = clean_ico(related_ico_match.group("ico")) if related_ico_match else ""
            if related_ico and related_ico == clean_ico(ico):
                continue

            snippet_start = max(0, match.start() - 260)
            snippet_end = min(len(html), match.end() + 260)
            snippet = _strip_tags(html[snippet_start:snippet_end])
            relationship_type = _detect_relationship_type(snippet)
            address = _extract_address(snippet)

            row = {
                "nazev": label,
                "firma": label,
                "jmeno": label,
                "ico": related_ico or None,
                "adresa": address,
                "typ_vazby": relationship_type or "vazba z veřejného agregátoru",
                "role": relationship_type or "nutno ověřit",
                "source_name": KURZY_SOURCE_NAME,
                "source_url": relationship_url,
                "confidence": "medium",
                "verification_status": "nutno ověřit",
                "stav_vazby": "Nutno ověřit",
                "zdroj_cast": KURZY_SOURCE_NAME,
                "entity_type": _detect_entity_type(label, relationship_type),
                "kurzy_vazby_link": relationship_url,
            }
            raw_rows.append(row)

        deduped_rows, skipped = _dedupe_relationships(raw_rows)
        result["relationships"] = deduped_rows
        result["diagnostics"] = {
            "kurzy_total_raw": len(raw_rows),
            "kurzy_total_deduped": len(deduped_rows),
            "kurzy_skipped_duplicates": skipped,
        }
        result["status"] = "ok" if deduped_rows else "nenalezeno"
    except requests.exceptions.Timeout:
        result["status"] = "failed"
        result["error"] = "Kurzy.cz neodpovědělo včas."
    except requests.exceptions.RequestException as exc:
        result["status"] = "failed"
        result["error"] = f"Chyba spojení s Kurzy.cz: {exc}"

    return result
