"""Fallback lookup přes Peníze.cz."""

from typing import Any

import requests

from core.config import HEADERS, PENIZE_REJSTRIK_SEARCH_URL, REQUEST_TIMEOUT


def fetch_penize_company_lookup(ico: str) -> dict[str, Any]:
    source_url = PENIZE_REJSTRIK_SEARCH_URL.format(ico=ico)
    result: dict[str, Any] = {
        "status": "not_found",
        "ico": ico,
        "nazev": None,
        "sidlo": None,
        "stav": None,
        "source_name": "Peníze.cz",
        "source_url": source_url,
        "confidence": "low",
        "error": None,
    }
    try:
        response = requests.get(source_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        if ico in response.text:
            result["status"] = "partial"
    except requests.exceptions.Timeout:
        result["status"] = "failed"
        result["error"] = "Peníze.cz neodpovědělo včas."
    except requests.exceptions.RequestException as exc:
        result["status"] = "failed"
        result["error"] = f"Chyba spojení s Peníze.cz: {exc}"
    return result
