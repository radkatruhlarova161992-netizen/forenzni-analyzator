"""Zdroj Justice.cz."""

from functools import lru_cache
import re
from typing import Any
from urllib.parse import quote

import requests

from core.config import (
    HEADERS,
    JUSTICE_REJSTRIK_API,
    JUSTICE_SBIRKA_URL,
    REQUEST_TIMEOUT,
)
from core.utils import clean_ico


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


def _normalize_company_name_for_match(value: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "", str(value or "").upper())


@lru_cache(maxsize=512)
def find_ico_by_company_name(company_name: str) -> str | None:
    normalized_target = _normalize_company_name_for_match(company_name)
    if not normalized_target:
        return None

    search_url = f"https://or.justice.cz/ias/ui/rejstrik-$firma?nazev={quote(company_name)}"
    try:
        response = requests.get(
            search_url,
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        text = response.text

        block_pattern = re.compile(
            r'<li[^>]*class="result[^"]*"[^>]*>(?P<block>.*?)</li>\s*</ul>',
            re.I | re.S,
        )
        result_pattern = re.compile(
            r'<th class="nowrap">Název subjektu:</th>\s*'
            r'<td><strong class="left">(?P<name>.*?)</strong>.*?'
            r'<th>IČO:</th>\s*<td class="right nowrap"><strong>\s*'
            r'(?P<ico_block>.*?)</strong>\s*</td>',
            re.I | re.S,
        )
        for block_match in block_pattern.finditer(text):
            block = block_match.group("block")
            match = result_pattern.search(block)
            if not match:
                continue

            matched_name = re.sub(r"<[^>]+>", "", match.group("name")).strip()
            if _normalize_company_name_for_match(matched_name) != normalized_target:
                continue

            ico = clean_ico(re.sub(r"\D", "", re.sub(r"<[^>]+>", "", match.group("ico_block"))))
            if ico:
                return ico
    except requests.exceptions.RequestException:
        return None

    return None
