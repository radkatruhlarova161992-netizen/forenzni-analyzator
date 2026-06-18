"""Kandidati firem podle nazvu nebo casti nazvu."""

from __future__ import annotations

from functools import lru_cache
from html import unescape
import re
from typing import Any

import requests

from core.config import ARES_SEARCH_URL, CANDIDATE_CACHE_MAX_AGE_DAYS, HEADERS, REQUEST_TIMEOUT
from core.utils import clean_ico, format_kurzy_search_link, normalize_name
from sources.justice import find_ico_by_company_name


def _strip_tags(value: str) -> str:
    return " ".join(unescape(re.sub(r"<[^>]+>", " ", str(value or ""))).split())


def _candidate_signature(candidate: dict[str, Any]) -> tuple[str, ...]:
    ico = clean_ico(str(candidate.get("ico") or ""))
    if ico:
        return ("ico", ico)
    return (
        "name_address",
        normalize_name(candidate.get("nazev") or ""),
        normalize_name(candidate.get("sidlo") or ""),
    )


def _dedupe_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, ...]] = set()
    for candidate in candidates:
        signature = _candidate_signature(candidate)
        if signature in seen:
            continue
        seen.add(signature)
        deduped.append(candidate)
    return deduped


@lru_cache(maxsize=512)
def search_company_candidates(query: str) -> list[dict[str, Any]]:
    """Najde kandidaty firmy bez automatickeho prirazeni nejisteho IČO."""
    normalized_query = " ".join(str(query or "").split())
    if len(normalized_query) < 3:
        return []

    candidates: list[dict[str, Any]] = []
    candidates.extend(_search_ares_candidates(normalized_query))
    candidates.extend(_search_justice_exact_candidate(normalized_query))
    candidates.extend(_search_kurzy_candidates(normalized_query))
    return _dedupe_candidates(candidates)


def _search_ares_candidates(query: str) -> list[dict[str, Any]]:
    try:
        response = requests.post(
            ARES_SEARCH_URL,
            headers={**HEADERS, "Content-Type": "application/json"},
            json={"obchodniJmeno": query, "pocet": 20},
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
    except (requests.exceptions.RequestException, ValueError):
        return []

    rows = data.get("ekonomickeSubjekty") if isinstance(data, dict) else None
    if not isinstance(rows, list):
        return []

    candidates: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        ico = clean_ico(str(row.get("ico") or ""))
        name = row.get("obchodniJmeno")
        if not name:
            continue
        sidlo = row.get("sidlo", {}) or {}
        candidates.append(
            {
                "ico": ico or None,
                "nazev": name,
                "sidlo": sidlo.get("textovaAdresa"),
                "source_name": "ARES",
                "source_url": ARES_SEARCH_URL,
                "confidence": "high",
                "verification_status": "candidate_match",
                "cache_ttl_days": CANDIDATE_CACHE_MAX_AGE_DAYS,
            }
        )
    return candidates


def _search_justice_exact_candidate(query: str) -> list[dict[str, Any]]:
    ico = find_ico_by_company_name(query)
    if not ico:
        return []
    return [
        {
            "ico": ico,
            "nazev": query,
            "sidlo": None,
            "source_name": "Justice.cz",
            "source_url": f"https://or.justice.cz/ias/ui/rejstrik-$firma?nazev={query}",
            "confidence": "high",
            "verification_status": "candidate_match",
            "cache_ttl_days": CANDIDATE_CACHE_MAX_AGE_DAYS,
        }
    ]


def _search_kurzy_candidates(query: str) -> list[dict[str, Any]]:
    source_url = format_kurzy_search_link(query, True)
    try:
        response = requests.get(source_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
    except requests.exceptions.RequestException:
        return []

    html = response.text
    if "captcha" in html.lower() or "id=\"loading\"" in html.lower():
        return []

    candidates: list[dict[str, Any]] = []
    anchor_pattern = re.compile(
        r'<a[^>]+href="(?P<href>[^"]+)"[^>]*>(?P<label>.*?)</a>',
        re.I | re.S,
    )
    for match in anchor_pattern.finditer(html):
        label = _strip_tags(match.group("label"))
        href = match.group("href")
        if len(label) < 3:
            continue
        ico_match = re.search(r"/(?P<ico>\d{8})/", href)
        ico = clean_ico(ico_match.group("ico")) if ico_match else ""
        if not ico and normalize_name(query) not in normalize_name(label):
            continue
        candidates.append(
            {
                "ico": ico or None,
                "nazev": label,
                "sidlo": None,
                "source_name": "Kurzy.cz",
                "source_url": source_url,
                "confidence": "medium" if ico else "low",
                "verification_status": "candidate_match",
                "cache_ttl_days": CANDIDATE_CACHE_MAX_AGE_DAYS,
            }
        )
    return candidates[:20]
