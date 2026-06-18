"""Fallback lookup přes Hlídač státu."""

from html import unescape
import re
from typing import Any

import requests

from core.config import HEADERS, HLIDAC_SUBJEKT_URL, REQUEST_TIMEOUT


def fetch_hlidac_company_lookup(ico: str) -> dict[str, Any]:
    source_url = HLIDAC_SUBJEKT_URL.format(ico=ico)
    result: dict[str, Any] = {
        "status": "not_found",
        "ico": ico,
        "nazev": None,
        "sidlo": None,
        "stav": None,
        "source_name": "Hlídač státu",
        "source_url": source_url,
        "confidence": "medium",
        "error": None,
    }
    try:
        response = requests.get(source_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        if response.status_code == 404:
            return result
        response.raise_for_status()
        text = response.text

        title_match = re.search(r"<title>(.*?)</title>", text, re.I | re.S)
        company_name = None
        if title_match:
            company_name = unescape(title_match.group(1)).split(" - Hlídač státu")[0].strip()

        if not company_name or company_name.lower() == "neplatné ico":
            return result

        result.update(
            {
                "status": "found",
                "nazev": company_name,
            }
        )
    except requests.exceptions.Timeout:
        result["status"] = "failed"
        result["error"] = "Hlídač státu neodpověděl včas."
    except requests.exceptions.RequestException as exc:
        result["status"] = "failed"
        result["error"] = f"Chyba spojení s Hlídačem státu: {exc}"

    return result
