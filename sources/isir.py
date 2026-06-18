"""Zdroj ISIR."""

from functools import lru_cache
from typing import Any

import requests

from core.config import HEADERS, ISIR_SEARCH_URL, REQUEST_TIMEOUT


@lru_cache(maxsize=256)
def fetch_isir_status(ico: str) -> dict[str, Any]:
    out: dict[str, Any] = {
        "isir_status": "neznámý",
        "isir_chyba": None,
        "probiha_insolvence": "nutno ověřit ručně",
        "link_isir": f"https://isir.justice.cz/isir/common/index.do#hledani-ic={ico}",
    }

    try:
        resp = requests.get(
            ISIR_SEARCH_URL,
            params={"ic": ico},
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        html = resp.text.lower()

        if "žádné záznamy" in html or "nenalezen" in html:
            out["probiha_insolvence"] = "Pravděpodobně ne (nutno ověřit)"
            out["isir_status"] = "ok"
        elif ico in resp.text:
            out["isir_status"] = "castecny_vysledek"
        else:
            out["isir_status"] = "vyzaduje_rucni_kontrolu"
    except requests.exceptions.Timeout:
        out["isir_status"] = "failed"
        out["isir_chyba"] = "ISIR neodpovědělo včas."
    except requests.exceptions.RequestException as exc:
        out["isir_status"] = "failed"
        out["isir_chyba"] = f"Chyba spojení s ISIR: {exc}"

    return out
