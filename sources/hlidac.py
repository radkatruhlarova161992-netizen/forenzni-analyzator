"""Fallback lookup a vazby přes Hlídač státu."""

from html import unescape
import re
from typing import Any

import requests

from core.config import HEADERS, HLIDAC_SUBJEKT_URL, REQUEST_TIMEOUT
from core.utils import format_role_status

HLIDAC_VAZBY_URL = "https://www.hlidacstatu.cz/subjekt/Vazby/{ico}"
HLIDAC_VAZBY_OSOBY_URL = "https://www.hlidacstatu.cz/subjekt/VazbyOsoby/{ico}"


def _strip_tags(value: str) -> str:
    return re.sub(r"<[^>]+>", "", unescape(value or "")).strip()


def _normalize_person_name(value: str) -> str:
    return re.sub(r"\s*\(\*?\d{4}\)\s*$", "", _strip_tags(value))


def _parse_hlidac_dates(start_date: str | None, end_date: str | None) -> tuple[str | None, str | None]:
    start = " ".join(str(start_date or "").split()) or None
    end = " ".join(str(end_date or "").split()) or None
    return start, end


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


def fetch_hlidac_relationships(ico: str, include_historical: bool = False) -> dict[str, Any]:
    result: dict[str, Any] = {
        "osoby": [],
        "navazane_firmy": [],
        "vr_status": "nenalezeno",
        "vr_chyba": None,
        "zdroj_vr": HLIDAC_VAZBY_OSOBY_URL.format(ico=ico),
        "zdroj_hlidac_vazby": HLIDAC_VAZBY_URL.format(ico=ico),
        "vazby_fallback_source_name": None,
        "vazby_fallback_note": None,
    }

    people_url = HLIDAC_VAZBY_OSOBY_URL.format(ico=ico)
    companies_url = HLIDAC_VAZBY_URL.format(ico=ico)

    try:
        people_response = requests.get(people_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        company_response = requests.get(companies_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        if people_response.status_code == 404 and company_response.status_code == 404:
            return result

        people_response.raise_for_status()
        company_response.raise_for_status()

        people_rows: list[dict[str, Any]] = []
        companies_rows: list[dict[str, Any]] = []
        historical_people_found = False
        historical_companies_found = False

        people_pattern = re.compile(
            r'<h4><a href="/osoba/[^"]+">(?P<name>[^<]+)</a></h4>\s*<ul>\s*<li>\s*'
            r'Od\s*(?P<od>[^<]+)\s*(?:<span>do\s*(?P<do>[^<]+)</span>)?\s*:\s*(?P<role>[^<]+)\s*</li>',
            re.I,
        )
        for match in people_pattern.finditer(people_response.text):
            person_name = _normalize_person_name(match.group("name"))
            if not person_name:
                continue
            start_date, end_date = _parse_hlidac_dates(match.group("od"), match.group("do"))
            is_current = not bool(end_date)
            if not include_historical and not is_current:
                historical_people_found = True
                continue
            people_rows.append(
                {
                    "jmeno": person_name,
                    "role": _strip_tags(match.group("role")),
                    "od": start_date,
                    "do": end_date,
                    "stav_vazby": format_role_status(is_current),
                    "zdroj_cast": "Hlídač státu",
                    "adresa": None,
                    "kurzy_vazby_link": people_url,
                }
            )

        companies_pattern = re.compile(
            r"<h4>(?P<company>[^<]+)</h4>\s*<br\s*/?>\s*.*?<i>/(?P<role>[^<]+)/</i>\s*v\s*"
            r"[^<]+\s*\((?P<od>[0-9. ]+)\s*-\s*(?P<do>[0-9. ]+)\)",
            re.I | re.S,
        )
        for match in companies_pattern.finditer(company_response.text):
            company_name = _strip_tags(match.group("company"))
            if not company_name:
                continue
            start_date, end_date = _parse_hlidac_dates(match.group("od"), match.group("do"))
            is_current = not bool(end_date)
            if not include_historical and not is_current:
                historical_companies_found = True
                continue
            companies_rows.append(
                {
                    "firma": company_name,
                    "ico": None,
                    "role": _strip_tags(match.group("role")),
                    "od": start_date,
                    "do": end_date,
                    "stav_vazby": format_role_status(is_current),
                    "zdroj_cast": "Hlídač státu",
                    "kurzy_vazby_link": companies_url,
                }
            )

        result["osoby"] = people_rows
        result["navazane_firmy"] = companies_rows
        result["vr_status"] = "ok" if (people_rows or companies_rows) else "nenalezeno"
        if people_rows or companies_rows:
            result["vazby_fallback_source_name"] = "Hlídač státu"
            result["vazby_fallback_note"] = (
                "Vazby byly dohledány přes Hlídač státu, protože primární zdroj je pro tento subjekt nevrátil."
            )
        elif historical_people_found or historical_companies_found:
            result["vr_status"] = "historical_only"
            result["vazby_fallback_source_name"] = "Hlídač státu"
            result["vazby_fallback_note"] = (
                "Pro tento subjekt jsou ve veřejných datech dohledané pouze historické vazby. "
                "Přepni zobrazení na „Aktuální i historické“."
            )
    except requests.exceptions.Timeout:
        result["vr_status"] = "failed"
        result["vr_chyba"] = "Hlídač státu neodpověděl včas."
    except requests.exceptions.RequestException as exc:
        result["vr_status"] = "failed"
        result["vr_chyba"] = f"Chyba spojení s Hlídačem státu: {exc}"

    return result
