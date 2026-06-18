"""Orchestrace načtení dat a normalizace entit mimo UI."""

from typing import Any

from core.utils import now_str
from models.company import Company
from models.person import Person
from sources.adis import fetch_dph_status
from sources.ares import fetch_ares_basic, fetch_ares_persons
from sources.isir import fetch_isir_status
from sources.justice import fetch_justice_person_relationships, fetch_sbirka_listin


def _should_try_person_relationship_lookup(
    ares_data: dict[str, Any],
    vr_data: dict[str, Any],
) -> bool:
    has_relationships = bool(vr_data.get("osoby") or vr_data.get("navazane_firmy"))
    is_physical_person = str(ares_data.get("pravni_forma") or "") == "101"
    return bool(is_physical_person and ares_data.get("nazev") and not has_relationships)


def fetch_company_data(ico: str, include_historical: bool = False) -> dict[str, Any]:
    """Načte data ze všech veřejných zdrojů bez UI logiky a bez analýzy."""
    ares_data = fetch_ares_basic(ico)
    vr_data = fetch_ares_persons(ico, include_historical=include_historical)
    if _should_try_person_relationship_lookup(ares_data, vr_data):
        person_vr_data = fetch_justice_person_relationships(
            ares_data.get("nazev") or "",
            ares_data.get("sidlo_raw") or ares_data.get("sidlo") or "",
            include_historical=include_historical,
        )
        if person_vr_data.get("navazane_firmy"):
            vr_data = person_vr_data
    dph_data = fetch_dph_status(ico)
    sbirka_data = fetch_sbirka_listin(ico, ares_data.get("nazev") or "")
    isir_data = fetch_isir_status(ico)

    return {
        "ico": ico,
        "include_historical": include_historical,
        "ares": ares_data,
        "vr": vr_data,
        "dph": dph_data,
        "sbirka": sbirka_data,
        "isir": isir_data,
    }


def normalize_entities(source_data: dict[str, Any]) -> dict[str, Any]:
    """Sloučí data ze zdrojů do jednotné firemní entity pro další analýzu."""
    record: dict[str, Any] = {
        "ico": source_data.get("ico"),
        "include_historical": source_data.get("include_historical", False),
        "cas_analyzy": now_str(),
    }
    record.update(source_data.get("ares", {}))
    record.update(source_data.get("vr", {}))
    record.update(source_data.get("dph", {}))
    record.update(source_data.get("sbirka", {}))
    record.update(source_data.get("isir", {}))
    return record


def company_from_record(record: dict[str, Any]) -> Company:
    return Company(
        ico=record.get("ico", ""),
        nazev=record.get("nazev"),
        sidlo=record.get("sidlo_raw") or record.get("sidlo"),
        pravni_forma=record.get("pravni_forma"),
        stav=record.get("stav"),
        v_likvidaci=bool(record.get("v_likvidaci")),
        datum_vzniku=record.get("datum_vzniku"),
        datum_zaniku=record.get("datum_zaniku"),
        zdroje={
            "ares": record.get("zdroj_ares", ""),
            "dph": record.get("zdroj_dph", ""),
            "sbirka": record.get("link_sbirka_listin", ""),
            "isir": record.get("link_isir", ""),
        },
        metadata={},
    )


def people_from_record(record: dict[str, Any]) -> list[Person]:
    people: list[Person] = []
    for item in record.get("osoby", []) or []:
        people.append(
            Person(
                jmeno=item.get("jmeno", ""),
                role=item.get("role"),
                adresa=item.get("adresa"),
                od=item.get("od"),
                do=item.get("do"),
                stav_vazby=item.get("stav_vazby"),
                zdroj=item.get("kurzy_vazby_link"),
                metadata={"zdroj_cast": item.get("zdroj_cast")},
            )
        )
    return people
