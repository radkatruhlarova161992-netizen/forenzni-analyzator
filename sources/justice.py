"""Zdroj Justice.cz."""

from functools import lru_cache
from typing import Any
from urllib.parse import quote

import requests

from core.config import (
    HEADERS,
    JUSTICE_REJSTRIK_API,
    JUSTICE_SBIRKA_URL,
    REQUEST_TIMEOUT,
)


@lru_cache(maxsize=256)
def fetch_sbirka_listin(ico: str, nazev_firmy: str = "") -> dict[str, Any]:
    out: dict[str, Any] = {
        "sbirka_status": "neznámý",
        "sbirka_chyba": None,
        "subjekt_id": None,
        "link_sbirka_listin": None,
        "link_rejstrik": f"https://or.justice.cz/ias/ui/rejstrik-$firma?nazev={quote(nazev_firmy)}&ico={ico}",
        "chybi_zaverky_2023_2025": "nutno ověřit ručně",
    }

    try:
        resp = requests.get(
            JUSTICE_REJSTRIK_API.format(ico=ico),
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()

        subjekty = data if isinstance(data, list) else data.get("subjekty") or data.get("items") or []
        if subjekty:
            subjekt = subjekty[0]
            subjekt_id = subjekt.get("subjektId") or subjekt.get("id")
            out["subjekt_id"] = subjekt_id
            if subjekt_id:
                out["link_sbirka_listin"] = JUSTICE_SBIRKA_URL.format(subjekt_id=subjekt_id)
            out["sbirka_status"] = "ok"
        else:
            out["sbirka_status"] = "nenalezeno"
    except requests.exceptions.Timeout:
        out["sbirka_status"] = "failed"
        out["sbirka_chyba"] = "Justice.cz neodpovědělo včas."
    except requests.exceptions.RequestException as exc:
        out["sbirka_status"] = "failed"
        out["sbirka_chyba"] = f"Chyba spojení s justice.cz: {exc}"
    except ValueError as exc:
        out["sbirka_status"] = "failed"
        out["sbirka_chyba"] = f"Nelze zpracovat odpověď justice.cz: {exc}"

    if not out["link_sbirka_listin"]:
        out["link_sbirka_listin"] = out["link_rejstrik"]

    return out
