"""Pomocné odkazy a dohledání přes Kurzy.cz."""

from typing import Any

import requests

from core.config import HEADERS, JUSTICE_VYPIS_URL, REQUEST_TIMEOUT
from core.utils import format_kurzy_search_link


def build_fallback_sources_for_ico(ico: str) -> dict[str, Any]:
    justice_link = JUSTICE_VYPIS_URL.format(ico=ico)
    kurzy_link = format_kurzy_search_link(ico, True)
    note = (
        "IČO nebylo nalezeno v ARES. Připraveno dohledání přes Justice.cz a Kurzy.cz."
    )
    found_elsewhere = False

    try:
        resp = requests.get(justice_link, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        if resp.status_code == 200 and ico in resp.text:
            found_elsewhere = True
            note = (
                "IČO nebylo nalezeno v ARES, ale objevuje se ve výsledku Justice.cz. "
                "Doporučena ruční kontrola."
            )
    except requests.exceptions.RequestException:
        pass

    return {
        "fallback_lookup_found": found_elsewhere,
        "fallback_lookup_note": note,
        "fallback_lookup_justice": justice_link,
        "fallback_lookup_kurzy": kurzy_link,
    }
