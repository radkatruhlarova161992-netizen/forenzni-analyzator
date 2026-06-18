"""Fallback lookup přes Detail.cz."""

from html import unescape
import re
from typing import Any

import requests

from core.config import DETAIL_COMPANY_URL, HEADERS, REQUEST_TIMEOUT


def fetch_detail_company_lookup(ico: str) -> dict[str, Any]:
    source_url = DETAIL_COMPANY_URL.format(ico=ico)
    result: dict[str, Any] = {
        "status": "not_found",
        "ico": ico,
        "nazev": None,
        "sidlo": None,
        "stav": None,
        "source_name": "Detail.cz",
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
        if ico not in text:
            return result

        title_match = re.search(r"<title>\s*Společnost\s*(.*?)\s*\|\s*Detail\.cz</title>", text, re.I | re.S)
        address_match = re.search(r"Adresa[^<]{0,80}</[^>]+>\s*<[^>]+>(.*?)<", text, re.I | re.S)
        active_match = re.search(r"\bAktivní\b", text, re.I)

        company_name = unescape(title_match.group(1)).strip() if title_match else None
        address = unescape(address_match.group(1)).strip() if address_match else None

        if not company_name:
            return result

        result.update(
            {
                "status": "found",
                "nazev": company_name,
                "sidlo": address,
                "stav": "Aktivní" if active_match else None,
            }
        )
    except requests.exceptions.Timeout:
        result["status"] = "failed"
        result["error"] = "Detail.cz neodpověděl včas."
    except requests.exceptions.RequestException as exc:
        result["status"] = "failed"
        result["error"] = f"Chyba spojení s Detail.cz: {exc}"

    return result
