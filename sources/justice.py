"""Zdroj Justice.cz."""

from functools import lru_cache
from html import unescape
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
from core.utils import clean_ico, format_kurzy_search_link


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


def _strip_html(value: str) -> str:
    return " ".join(unescape(re.sub(r"<[^>]+>", " ", str(value or ""))).split())


def _normalize_text_for_match(value: str) -> str:
    return re.sub(r"[^A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ0-9]+", "", str(value or "").upper())


def _normalize_address_for_match(value: str) -> str:
    return re.sub(r"[^A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ0-9]+", "", str(value or "").upper())


def _split_person_name(person_name: str) -> tuple[str, str] | None:
    ignored_titles = {
        "BC",
        "DIS",
        "DOC",
        "ING",
        "JUDR",
        "MGR",
        "MUDR",
        "PHARMDR",
        "PHDR",
        "PROF",
        "RNDR",
    }
    parts = [
        part.strip(".,")
        for part in str(person_name or "").split()
        if part.strip(".,").upper() not in ignored_titles
    ]
    if len(parts) < 2:
        return None
    return parts[0], parts[-1]


def _extract_table_value(block: str, label: str) -> str:
    match = re.search(
        rf"<th[^>]*>\s*{re.escape(label)}\s*:?\s*</th>\s*<td[^>]*>(?P<value>.*?)</td>",
        block,
        re.I | re.S,
    )
    return _strip_html(match.group("value")) if match else ""


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


@lru_cache(maxsize=512)
def fetch_justice_person_relationships(
    person_name: str,
    source_address: str = "",
    include_historical: bool = False,
) -> dict[str, Any]:
    name_parts = _split_person_name(person_name)
    source_url = ""
    out: dict[str, Any] = {
        "osoby": [],
        "navazane_firmy": [],
        "vr_status": "nenalezeno",
        "vr_chyba": None,
        "zdroj_vr": source_url,
        "zdroj_justice_osoba": source_url,
    }
    if not name_parts:
        out["vr_chyba"] = "Jméno osoby nelze bezpečně rozdělit pro vyhledání v Justice.cz."
        return out

    first_name, last_name = name_parts
    source_url = (
        "https://or.justice.cz/ias/ui/rejstrik-$osoba?"
        f"jmeno={quote(first_name)}&prijmeni={quote(last_name)}"
    )
    out["zdroj_vr"] = source_url
    out["zdroj_justice_osoba"] = source_url

    expected_name = _normalize_text_for_match(f"{first_name} {last_name}")
    expected_address = _normalize_address_for_match(source_address)

    try:
        response = requests.get(source_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        text = response.text
        if not text.strip():
            raise ValueError("Prázdná odpověď Justice.cz.")

        blocks = re.findall(
            r'<li[^>]*class="result[^"]*"[^>]*>(?P<block>.*?)</li>\s*</ul>',
            text,
            re.I | re.S,
        )
        rows: list[dict[str, Any]] = []
        for block in blocks:
            result_person_name = _extract_table_value(block, "Jméno")
            if result_person_name and _normalize_text_for_match(result_person_name) != expected_name:
                continue

            result_address = _extract_table_value(block, "Adresa")
            normalized_result_address = _normalize_address_for_match(result_address)
            if expected_address and normalized_result_address:
                if expected_address not in normalized_result_address and normalized_result_address not in expected_address:
                    continue

            company_match = re.search(
                r'<th[^>]*class="nowrap"[^>]*>\s*Název subjektu:\s*</th>\s*'
                r'<td[^>]*><strong[^>]*class="left"[^>]*>(?P<name>.*?)</strong>.*?'
                r"<th[^>]*>\s*IČO:\s*</th>\s*<td[^>]*>\s*<strong>\s*"
                r"(?P<ico_block>.*?)</strong>\s*</td>",
                block,
                re.I | re.S,
            )
            if not company_match:
                continue

            company_name = _strip_html(company_match.group("name"))
            company_ico = clean_ico(re.sub(r"\D", "", _strip_html(company_match.group("ico_block"))))
            if not company_name or not company_ico:
                continue

            role = _extract_table_value(block, "Angažmá") or "Vazba osoby na firmu"
            rows.append(
                {
                    "firma": company_name,
                    "ico": company_ico,
                    "role": role,
                    "od": None,
                    "do": None,
                    "stav_vazby": "Aktuální",
                    "zdroj_cast": "Justice.cz - vyhledání osoby",
                    "kurzy_vazby_link": source_url,
                    "zdroj_url": source_url,
                }
            )

        seen: set[tuple[Any, ...]] = set()
        deduped: list[dict[str, Any]] = []
        for row in rows:
            signature = (row.get("firma"), row.get("ico"), row.get("role"))
            if signature in seen:
                continue
            seen.add(signature)
            deduped.append(row)

        out["navazane_firmy"] = deduped
        out["vr_status"] = "ok" if deduped else "nenalezeno"
        out["vazby_fallback_note"] = (
            "U fyzické osoby byly vazby dohledány přes vyhledání osoby v Justice.cz. "
            "Údaje doporučujeme ověřit ve zdroji."
        )
        return out
    except requests.exceptions.Timeout:
        out["vr_status"] = "failed"
        out["vr_chyba"] = "Justice.cz neodpovědělo včas při hledání vazeb osoby."
    except requests.exceptions.RequestException as exc:
        out["vr_status"] = "failed"
        out["vr_chyba"] = f"Chyba spojení s Justice.cz při hledání vazeb osoby: {exc}"
    except ValueError as exc:
        out["vr_status"] = "failed"
        out["vr_chyba"] = f"Nelze zpracovat odpověď Justice.cz pro osobu: {exc}"

    if not out["navazane_firmy"]:
        out["manual_verification_urls"] = {
            "Justice.cz": source_url,
            "Kurzy.cz": format_kurzy_search_link(person_name, not include_historical),
        }
    return out
