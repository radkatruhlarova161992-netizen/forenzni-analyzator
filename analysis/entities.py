"""Orchestrace načtení dat a normalizace entit mimo UI."""

from typing import Any

from core.database import load_cached_source_data, save_cached_source_data
from core.utils import now_str
from analysis.source_diagnostics import build_external_gap_warning, build_source_diagnostics
from models.company import Company
from models.person import Person
from sources.adis import fetch_dph_status
from sources.ares import fetch_ares_basic, fetch_ares_persons
from sources.isir import fetch_isir_status
from sources.justice import fetch_justice_person_relationships, fetch_sbirka_listin
from sources.kurzy_relationships import fetch_kurzy_relationships


def _should_try_person_relationship_lookup(
    ares_data: dict[str, Any],
    vr_data: dict[str, Any],
) -> bool:
    has_relationships = bool(vr_data.get("osoby") or vr_data.get("navazane_firmy"))
    is_physical_person = str(ares_data.get("pravni_forma") or "") == "101"
    return bool(is_physical_person and ares_data.get("nazev") and not has_relationships)


def clear_source_function_caches() -> None:
    fetch_ares_basic.cache_clear()
    fetch_ares_persons.cache_clear()
    fetch_dph_status.cache_clear()
    fetch_sbirka_listin.cache_clear()
    fetch_justice_person_relationships.cache_clear()
    fetch_isir_status.cache_clear()


def _fetch_company_data_from_sources(
    ico: str,
    include_historical: bool = False,
    include_public_aggregators: bool = False,
) -> dict[str, Any]:
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
    kurzy_relationships_data = (
        fetch_kurzy_relationships(ico) if include_public_aggregators else None
    )

    return {
        "ico": ico,
        "include_historical": include_historical,
        "include_public_aggregators": include_public_aggregators,
        "ares": ares_data,
        "vr": vr_data,
        "dph": dph_data,
        "sbirka": sbirka_data,
        "isir": isir_data,
        "kurzy_relationships": kurzy_relationships_data,
    }


def fetch_company_data(
    ico: str,
    include_historical: bool = False,
    include_public_aggregators: bool = False,
    force_refresh: bool = False,
) -> dict[str, Any]:
    """Načte data z lokální cache nebo z veřejných zdrojů bez UI logiky."""
    if not force_refresh:
        cached_data = load_cached_source_data(
            ico,
            include_historical,
            include_public_aggregators,
        )
        if cached_data:
            return cached_data

    clear_source_function_caches()
    source_data = _fetch_company_data_from_sources(
        ico,
        include_historical=include_historical,
        include_public_aggregators=include_public_aggregators,
    )
    save_cached_source_data(
        ico,
        include_historical,
        include_public_aggregators,
        source_data,
    )
    return source_data


def _build_primary_relationship_diagnostics(record: dict[str, Any]) -> dict[str, int]:
    ares_count = 0
    justice_count = 0
    for person in record.get("osoby", []) or []:
        source = str(person.get("zdroj_cast") or "")
        if "Justice" in source:
            justice_count += 1
        else:
            ares_count += 1
    for company in record.get("navazane_firmy", []) or []:
        source = str(company.get("zdroj_cast") or "")
        if "Justice" in source:
            justice_count += 1
        else:
            ares_count += 1
    return {
        "ares": ares_count,
        "justice": justice_count,
    }


def _relationship_signature(item: dict[str, Any]) -> tuple[str, ...]:
    ico = str(item.get("ico") or "").strip()
    if ico:
        return ("ico", ico)
    return (
        "name_address",
        " ".join(str(item.get("firma") or item.get("nazev") or "").lower().split()),
        " ".join(str(item.get("adresa") or "").lower().split()),
    )


def _merge_relationships(
    primary_relationships: list[dict[str, Any]],
    kurzy_relationships: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], int]:
    merged: list[dict[str, Any]] = []
    skipped = 0
    seen: set[tuple[str, ...]] = set()

    for relationship in primary_relationships:
        normalized = {
            **relationship,
            "source_name": relationship.get("source_name")
            or (
                "Justice.cz"
                if "Justice" in str(relationship.get("zdroj_cast") or "")
                else "ARES / veřejný rejstřík"
            ),
            "source_url": relationship.get("source_url")
            or relationship.get("kurzy_vazby_link"),
            "confidence": relationship.get("confidence") or "high",
            "verification_status": relationship.get("verification_status")
            or "verified_primary",
            "verification_label": relationship.get("verification_label")
            or "ověřeno primárním zdrojem",
        }
        signature = _relationship_signature(normalized)
        if signature in seen:
            skipped += 1
            continue
        seen.add(signature)
        merged.append(normalized)

    for relationship in kurzy_relationships:
        normalized = {
            **relationship,
            "source_name": relationship.get("source_name") or "Kurzy.cz",
            "source_url": relationship.get("source_url")
            or relationship.get("kurzy_vazby_link"),
            "confidence": relationship.get("confidence") or "medium",
            "verification_status": relationship.get("verification_status")
            or "unverified_external",
            "verification_label": relationship.get("verification_label") or "nutno ověřit",
        }
        signature = _relationship_signature(normalized)
        if signature in seen:
            skipped += 1
            continue
        seen.add(signature)
        merged.append(normalized)

    return merged, skipped


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

    primary_diagnostics = _build_primary_relationship_diagnostics(record)
    kurzy_data = source_data.get("kurzy_relationships") or {}
    kurzy_relationships = kurzy_data.get("relationships", []) or []
    merged_relationships, merged_skipped = _merge_relationships(
        record.get("navazane_firmy", []) or [],
        kurzy_relationships,
    )
    record["navazane_firmy"] = merged_relationships
    record["relationship_diagnostics"] = {
        "ares": primary_diagnostics["ares"],
        "justice": primary_diagnostics["justice"],
        "kurzy": len(kurzy_relationships),
        "merged": len(merged_relationships),
        "skipped": merged_skipped,
    }
    record["source_diagnostics"] = build_source_diagnostics(
        record,
        source_data=source_data,
        merged_skipped=merged_skipped,
    )
    diagnostics_counts = record["source_diagnostics"]["counts"]
    record["verified_relationship_count"] = diagnostics_counts["verified_relationships"]
    record["unverified_external_relationship_count"] = len(
        [
            item
            for item in merged_relationships
            if item.get("verification_status") == "unverified_external"
        ]
    )
    record["pending_ico_relationship_count"] = len(
        [
            item
            for item in merged_relationships
            if item.get("verification_status") == "unverified_external"
            and not item.get("ico")
        ]
    )
    record["external_gap_warning"] = build_external_gap_warning(record)
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
