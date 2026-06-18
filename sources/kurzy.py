"""Pomocné odkazy a dohledání přes Kurzy.cz."""

from typing import Any

from core.config import JUSTICE_VYPIS_URL
from core.utils import format_kurzy_search_link


def build_fallback_sources_for_ico(ico: str) -> dict[str, Any]:
    justice_link = JUSTICE_VYPIS_URL.format(ico=ico)
    kurzy_link = format_kurzy_search_link(ico, True)
    hlidac_link = f"https://www.hlidacstatu.cz/subjekt/{ico}"
    note = (
        "IČO nebylo nalezeno v ARES. Připraveno dohledání přes Justice.cz a Kurzy.cz."
    )

    return {
        "fallback_lookup_found": False,
        "fallback_lookup_note": note,
        "fallback_lookup_justice": justice_link,
        "fallback_lookup_kurzy": kurzy_link,
        "fallback_lookup_hlidac": hlidac_link,
    }
