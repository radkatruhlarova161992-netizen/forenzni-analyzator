"""Zdroj ARES."""

from functools import lru_cache
from typing import Any

import requests

from core.config import ARES_URL, ARES_VR_URL, HEADERS, JUSTICE_VYPIS_URL, REQUEST_TIMEOUT
from core.utils import clean_ico, format_kurzy_search_link, format_role_status
from sources.company_lookup import find_company_by_ico
from sources.hlidac import fetch_hlidac_relationships
from sources.kurzy import build_fallback_sources_for_ico


def extract_date_range(node: dict[str, Any]) -> tuple[str | None, str | None]:
    membership = node.get("clenstvi") or {}
    membership_dates = membership.get("clenstvi") or {}
    role_dates = membership.get("funkce") or {}

    start_date = (
        node.get("datumZapisu")
        or node.get("clenstviOd")
        or membership_dates.get("vznikClenstvi")
        or role_dates.get("vznikFunkce")
        or node.get("vznik")
    )
    end_date = (
        node.get("datumVymazu")
        or node.get("clenstviDo")
        or membership_dates.get("zanikClenstvi")
        or role_dates.get("zanikFunkce")
        or node.get("zanik")
    )
    return start_date, end_date


def is_current_relationship(node: dict[str, Any]) -> bool:
    _, end_date = extract_date_range(node)
    return not bool(end_date)


def build_person_name(person: dict[str, Any]) -> str:
    if not person:
        return ""
    return " ".join(
        filter(
            None,
            [
                person.get("titulPredJmenem"),
                person.get("jmeno"),
                person.get("prijmeni"),
                person.get("titulZaJmenem"),
            ],
        )
    ).strip()


def dedupe_relationships(rows: list[dict[str, Any]], keys: tuple[str, ...]) -> list[dict[str, Any]]:
    seen: set[tuple[Any, ...]] = set()
    deduped: list[dict[str, Any]] = []
    for row in rows:
        signature = tuple(row.get(key) for key in keys)
        if signature in seen:
            continue
        seen.add(signature)
        deduped.append(row)
    return deduped


def add_person_relationship(
    target: list[dict[str, Any]],
    node: dict[str, Any],
    role: str,
    source: str,
    include_historical: bool,
) -> None:
    person = node.get("fyzickaOsoba") or {}
    name = build_person_name(person)
    if not name:
        return

    start_date, end_date = extract_date_range(node)
    current = is_current_relationship(node)
    if not include_historical and not current:
        return

    target.append(
        {
            "jmeno": name,
            "role": role,
            "od": start_date,
            "do": end_date,
            "stav_vazby": format_role_status(current),
            "zdroj_cast": source,
            "adresa": (person.get("adresa") or {}).get("textovaAdresa"),
            "kurzy_vazby_link": format_kurzy_search_link(name, not include_historical),
        }
    )


def add_company_relationship(
    target: list[dict[str, Any]],
    node: dict[str, Any],
    role: str,
    source: str,
    include_historical: bool,
) -> None:
    company = node.get("pravnickaOsoba") or {}
    company_name = company.get("obchodniJmeno")
    if not company_name:
        return

    start_date, end_date = extract_date_range(node)
    current = is_current_relationship(node)
    if not include_historical and not current:
        return

    company_ico = clean_ico(company.get("ico") or "")
    target.append(
        {
            "firma": company_name,
            "ico": company_ico or None,
            "role": role,
            "od": start_date,
            "do": end_date,
            "stav_vazby": format_role_status(current),
            "zdroj_cast": source,
            "kurzy_vazby_link": format_kurzy_search_link(
                company_ico or company_name, not include_historical
            ),
        }
    )


@lru_cache(maxsize=256)
def fetch_ares_basic(ico: str) -> dict[str, Any]:
    result: dict[str, Any] = {
        "ico": ico,
        "nazev": None,
        "sidlo": None,
        "pravni_forma": None,
        "stav": None,
        "v_likvidaci": False,
        "datum_vzniku": None,
        "datum_zaniku": None,
        "zdroj_ares": ARES_URL.format(ico=ico),
        "ares_status": "neznámý",
        "ares_chyba": None,
        "fallback_lookup_found": False,
        "fallback_lookup_note": None,
        "fallback_lookup_justice": JUSTICE_VYPIS_URL.format(ico=ico),
        "fallback_lookup_kurzy": format_kurzy_search_link(ico, True),
        "fallback_lookup_hlidac": None,
        "fallback_lookup_source_name": None,
        "fallback_lookup_source_url": None,
        "fallback_lookup_confidence": None,
        "fallback_lookup_attempts": [],
    }

    try:
        resp = requests.get(
            ARES_URL.format(ico=ico), headers=HEADERS, timeout=REQUEST_TIMEOUT
        )
        if resp.status_code == 404:
            result["ares_status"] = "nenalezeno_v_ares"
            result.update(build_fallback_sources_for_ico(ico))
            lookup_result = find_company_by_ico(ico).to_dict()
            result["fallback_lookup_attempts"] = lookup_result.get("attempts", [])
            result["fallback_lookup_hlidac"] = lookup_result.get("manual_verification_urls", {}).get("Hlídač státu")
            if lookup_result.get("status") == "found":
                result["nazev"] = lookup_result.get("nazev")
                result["sidlo"] = lookup_result.get("sidlo")
                result["sidlo_raw"] = lookup_result.get("sidlo")
                result["stav"] = lookup_result.get("stav") or "Nutno ověřit ručně"
                result["fallback_lookup_found"] = True
                result["fallback_lookup_source_name"] = lookup_result.get("source_name")
                result["fallback_lookup_source_url"] = lookup_result.get("source_url")
                result["fallback_lookup_confidence"] = lookup_result.get("confidence")
                result["fallback_lookup_note"] = (
                    "Firma nebyla nalezena v primárním zdroji, ale byla dohledána přes "
                    f"{lookup_result.get('source_name')}. Údaje doporučujeme ověřit ručně."
                )
            else:
                result["nazev"] = "(IČO nenalezeno v ARES)"
                result["fallback_lookup_note"] = "Subjekt se nepodařilo automaticky dohledat. Ověřte ručně."
            return result

        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, dict):
            raise ValueError("Odpověď ARES není JSON objekt.")

        result["nazev"] = data.get("obchodniJmeno")
        result["pravni_forma"] = data.get("pravniForma")
        result["datum_vzniku"] = data.get("datumVzniku")
        result["datum_zaniku"] = data.get("datumZaniku")

        sidlo = data.get("sidlo", {}) or {}
        adresa_parts = [
            sidlo.get("nazevUlice") or sidlo.get("nazevCastiObce"),
            sidlo.get("cisloDomovni") and str(sidlo.get("cisloDomovni")),
            sidlo.get("nazevObce"),
            sidlo.get("psc") and str(sidlo.get("psc")),
        ]
        result["sidlo"] = ", ".join([p for p in adresa_parts if p])
        result["sidlo_raw"] = sidlo.get("textovaAdresa") or result["sidlo"]

        full_text_check = str(data).lower()
        if "likvidace" in full_text_check or "v likvidaci" in str(result["nazev"] or "").lower():
            result["v_likvidaci"] = True

        if result["datum_zaniku"]:
            result["stav"] = "Zaniklý subjekt"
        else:
            result["stav"] = "Aktivní" if not result["v_likvidaci"] else "V likvidaci"

        result["ares_status"] = "ok"
    except requests.exceptions.Timeout:
        result["ares_status"] = "failed"
        result["ares_chyba"] = "ARES neodpovědělo včas (timeout)."
    except requests.exceptions.RequestException as exc:
        result["ares_status"] = "failed"
        result["ares_chyba"] = f"Chyba spojení s ARES: {exc}"
    except (ValueError, KeyError) as exc:
        result["ares_status"] = "failed"
        result["ares_chyba"] = f"Neočekávaný formát odpovědi ARES: {exc}"

    if result["ares_status"] == "failed":
        lookup_result = find_company_by_ico(ico).to_dict()
        result["fallback_lookup_attempts"] = lookup_result.get("attempts", [])
        result["fallback_lookup_hlidac"] = lookup_result.get("manual_verification_urls", {}).get("Hlídač státu")
        if lookup_result.get("status") == "found":
            result["nazev"] = lookup_result.get("nazev")
            result["sidlo"] = lookup_result.get("sidlo")
            result["sidlo_raw"] = lookup_result.get("sidlo")
            result["stav"] = lookup_result.get("stav") or result.get("stav")
            result["fallback_lookup_found"] = True
            result["fallback_lookup_source_name"] = lookup_result.get("source_name")
            result["fallback_lookup_source_url"] = lookup_result.get("source_url")
            result["fallback_lookup_confidence"] = lookup_result.get("confidence")
            result["fallback_lookup_note"] = (
                "Firma nebyla nalezena v primárním zdroji, ale byla dohledána přes "
                f"{lookup_result.get('source_name')}. Údaje doporučujeme ověřit ručně."
            )
        else:
            result["fallback_lookup_note"] = "Subjekt se nepodařilo automaticky dohledat. Ověřte ručně."

    return result


@lru_cache(maxsize=256)
def fetch_ares_persons(ico: str, include_historical: bool = False) -> dict[str, Any]:
    out: dict[str, Any] = {
        "osoby": [],
        "navazane_firmy": [],
        "vr_status": "neznámý",
        "vr_chyba": None,
        "zdroj_vr": ARES_VR_URL.format(ico=ico),
    }
    try:
        resp = requests.get(
            ARES_VR_URL.format(ico=ico), headers=HEADERS, timeout=REQUEST_TIMEOUT
        )
        if resp.status_code == 404:
            hlidac_result = fetch_hlidac_relationships(
                ico,
                include_historical=include_historical,
            )
            if (
                hlidac_result.get("osoby")
                or hlidac_result.get("navazane_firmy")
                or hlidac_result.get("vr_status") == "historical_only"
            ):
                return hlidac_result
            out["vr_status"] = "nenalezeno"
            return out

        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, dict):
            raise ValueError("Odpověď ARES VR není JSON objekt.")

        zaznamy = data.get("zaznamy") or [data]
        for zaznam in zaznamy:
            for organ in zaznam.get("statutarniOrgany", []) or []:
                role_name = organ.get("nazevOrganu") or "Statutární orgán"
                for member in organ.get("clenoveOrganu", []) or []:
                    member_role = (
                        ((member.get("clenstvi") or {}).get("funkce") or {}).get("nazev")
                        or member.get("nazevAngazma")
                        or role_name
                    )
                    add_person_relationship(out["osoby"], member, member_role, role_name, include_historical)
                    add_company_relationship(
                        out["navazane_firmy"], member, member_role, role_name, include_historical
                    )

            for organ in zaznam.get("ostatniOrgany", []) or []:
                role_name = organ.get("nazevOrganu") or "Další orgán"
                for member in organ.get("clenoveOrganu", []) or []:
                    member_role = (
                        ((member.get("clenstvi") or {}).get("funkce") or {}).get("nazev")
                        or member.get("nazevAngazma")
                        or role_name
                    )
                    add_person_relationship(out["osoby"], member, member_role, role_name, include_historical)
                    add_company_relationship(
                        out["navazane_firmy"], member, member_role, role_name, include_historical
                    )

            for ownership_group in zaznam.get("spolecnici", []) or []:
                role_name = ownership_group.get("nazevOrganu") or "Společník"
                for partner in ownership_group.get("spolecnik", []) or []:
                    partner_node = partner.get("osoba") or partner
                    add_person_relationship(out["osoby"], partner_node, role_name, role_name, include_historical)
                    add_company_relationship(
                        out["navazane_firmy"], partner_node, role_name, role_name, include_historical
                    )

            for shareholder_group in zaznam.get("akcionari", []) or []:
                role_name = shareholder_group.get("typOrganu") or "Akcionář"
                for shareholder in shareholder_group.get("clenoveOrganu", []) or []:
                    add_person_relationship(out["osoby"], shareholder, role_name, role_name, include_historical)
                    add_company_relationship(
                        out["navazane_firmy"], shareholder, role_name, role_name, include_historical
                    )

        out["osoby"] = dedupe_relationships(
            out["osoby"], ("jmeno", "role", "od", "do", "stav_vazby")
        )
        out["navazane_firmy"] = dedupe_relationships(
            out["navazane_firmy"], ("firma", "ico", "role", "od", "do", "stav_vazby")
        )
        if out["osoby"] or out["navazane_firmy"]:
            out["vr_status"] = "ok"
            return out

        hlidac_result = fetch_hlidac_relationships(
            ico,
            include_historical=include_historical,
        )
        if (
            hlidac_result.get("osoby")
            or hlidac_result.get("navazane_firmy")
            or hlidac_result.get("vr_status") == "historical_only"
        ):
            return hlidac_result
        out["vr_status"] = "ok"
    except requests.exceptions.Timeout:
        out["vr_status"] = "failed"
        out["vr_chyba"] = "Veřejný rejstřík (ARES VR) neodpověděl včas."
    except requests.exceptions.RequestException as exc:
        out["vr_status"] = "failed"
        out["vr_chyba"] = f"Chyba spojení s ARES VR: {exc}"
    except (ValueError, KeyError) as exc:
        out["vr_status"] = "failed"
        out["vr_chyba"] = f"Neočekávaný formát odpovědi ARES VR: {exc}"

    if out["vr_status"] in {"failed", "nenalezeno"}:
        hlidac_result = fetch_hlidac_relationships(
            ico,
            include_historical=include_historical,
        )
        if (
            hlidac_result.get("osoby")
            or hlidac_result.get("navazane_firmy")
            or hlidac_result.get("vr_status") == "historical_only"
        ):
            return hlidac_result

    return out
