"""Rizene rozsireni site vztahu bez vazby na Streamlit UI."""

from __future__ import annotations

from collections import deque
from typing import Any

from analysis.entities import fetch_company_data, normalize_entities
from analysis.risk import calculate_risk_signals
from core.utils import clean_ico, normalize_name
from sources.company_search import search_company_candidates
from analysis.expansion_helpers import (
    expand_by_person,
    expand_by_address,
    resolve_candidate_company,
)

MAX_NEW_COMPANIES_PER_SEED = 150
MAX_TOTAL_ENTITIES = 1000
MAX_DEPTH = 3


def _normalize_address(address: str | None) -> str:
    """Normalizuje adresu pro porovnání."""
    if not address:
        return ""
    return " ".join(str(address or "").lower().split())


def collect_expansion_targets(
    record: dict[str, Any],
    include_external: bool,
    include_person_expansion: bool = True,
    include_address_expansion: bool = True,
) -> list[dict[str, Any]]:
    """
    Sbírá cíle k rozšíření sítě (firmy, osoby, adresy) z jednoho záznamu.

    Vrací seznam položek:
    {
        "target_type": "company" | "person" | "address",
        "value": "...",  # IČO, jméno, nebo adresa
        "source_ico": "...",
        "source_name": "...",
        "relation_type": "...",
        "confidence": "...",
        "verification_status": "..."
    }
    """
    targets: list[dict[str, Any]] = []
    source_ico = record.get("ico")
    source_name = record.get("nazev") or "(neznámý název)"

    # 1. Navázané firmy
    for company in record.get("navazane_firmy", []) or []:
        if not include_external and company.get("verification_status") == "unverified_external":
            continue

        ico = clean_ico(str(company.get("ico") or ""))

        # Pokud má IČO, přidej firmu
        if ico and ico != source_ico:
            targets.append({
                "target_type": "company",
                "value": ico,
                "source_ico": source_ico,
                "source_name": source_name,
                "relation_type": company.get("role") or company.get("relationship_type") or "vazba",
                "confidence": company.get("confidence") or "medium",
                "verification_status": company.get("verification_status") or "verified_primary",
                "is_historical": company.get("is_historical") or (
                    bool(company.get("do")) or company.get("stav_vazby") == "Historická"
                ),
                "source_name_company": company.get("firma"),
                "source_url": company.get("source_url"),
            })
        else:
            # Bez IČO - pokus se najít kandidáty podle jména
            firm_name = company.get("firma") or company.get("nazev")
            if firm_name and firm_name != source_name:
                targets.append({
                    "target_type": "company",
                    "value": firm_name,
                    "is_name_search": True,
                    "source_ico": source_ico,
                    "source_name": source_name,
                    "relation_type": company.get("role") or company.get("relationship_type") or "vazba",
                    "confidence": "low",
                    "verification_status": "candidate_needs_resolution",
                    "is_historical": company.get("is_historical") or (
                        bool(company.get("do")) or company.get("stav_vazby") == "Historická"
                    ),
                    "source_name_company": firm_name,
                    "source_url": company.get("source_url"),
                })

    # 2. Osoby - hledání dalších firem přes osobu
    if include_person_expansion:
        for person in record.get("osoby", []) or []:
            person_name = person.get("jmeno")
            if person_name and person_name != source_name:
                targets.append({
                    "target_type": "person",
                    "value": normalize_name(person_name),
                    "source_ico": source_ico,
                    "source_name": source_name,
                    "relation_type": person.get("role") or "osoba",
                    "confidence": "medium" if person.get("od") or person.get("do") else "low",
                    "verification_status": "verified_primary",
                    "person_full_name": person_name,
                    "person_role": person.get("role"),
                    "is_historical": bool(person.get("do")) or person.get("stav_vazby") == "Historická",
                })

    # 3. Adresy - hledání dalších firem na stejné adrese
    if include_address_expansion:
        company_address = record.get("sidlo_raw") or record.get("sidlo")
        if company_address:
            normalized_addr = _normalize_address(company_address)
            if normalized_addr:
                targets.append({
                    "target_type": "address",
                    "value": normalized_addr,
                    "raw_address": company_address,
                    "source_ico": source_ico,
                    "source_name": source_name,
                    "relation_type": "sídlo",
                    "confidence": "high",
                    "verification_status": "verified_primary",
                    "address_type": "current_address",
                })

        # Historické adresy osob
        for person in record.get("osoby", []) or []:
            person_address = person.get("adresa")
            if person_address:
                normalized_addr = _normalize_address(person_address)
                if normalized_addr:
                    targets.append({
                        "target_type": "address",
                        "value": normalized_addr,
                        "raw_address": person_address,
                        "source_ico": source_ico,
                        "source_name": source_name,
                        "relation_type": f"adresa osoby ({person.get('jmeno')})",
                        "confidence": "medium",
                        "verification_status": "verified_primary",
                        "address_type": "person_address",
                    })

    return targets


def _search_companies_by_person_name(
    person_name: str,
    source_url: str | None = None,
) -> list[dict[str, Any]]:
    """
    Hledá firmy, kde se daná osoba objevuje.
    Používá expansion_helpers.expand_by_person a vrací kandidáty.
    """
    results: list[dict[str, Any]] = []
    candidates = expand_by_person(person_name)

    for candidate in candidates:
        ico = candidate.get("ico")
        if ico:
            results.append({
                "ico": ico,
                "confidence": candidate.get("confidence", "low"),
                "verification_status": candidate.get("verification_status", "candidate_needs_resolution"),
                "source_name": candidate.get("source_name"),
                "source_url": candidate.get("source_url") or source_url,
            })

    return results


def _search_companies_by_address(
    address: str,
) -> list[dict[str, Any]]:
    """
    Hledá firmy na stejné adrese pomocí kombinace ARES/ Kurzy/ company_search.
    Deleguje na analysis.expansion_helpers.expand_by_address.
    """
    return expand_by_address(address)


def _search_companies_by_name(
    company_name: str,
) -> list[dict[str, Any]]:
    """
    Hledá firmu podle názvu a vrací kandidáty s IČO.
    Používá search_company_candidates jako dříve.
    """
    results: list[dict[str, Any]] = []
    candidates = search_company_candidates(company_name)

    for candidate in candidates:
        if candidate.get("ico"):
            results.append({
                "ico": candidate["ico"],
                "name": candidate.get("nazev"),
                "confidence": candidate.get("confidence", "low"),
                "verification_status": "candidate_match",
                "source_name": candidate.get("source_name"),
                "source_url": candidate.get("source_url"),
            })

    return results


def expand_relationship_network(
    seed_icos: list[str],
    depth: int,
    include_external: bool,
    include_historical: bool = False,
    include_person_expansion: bool = True,
    include_address_expansion: bool = True,
    force_refresh: bool = False,
) -> dict[str, Any]:
    """
    Načte viceurovnovou síť s deduplikací a ochrannými limity.

    Fronta nyní podporuje:
    - ("company_ico", ico, None)
    - ("company_name", name, None)
    - ("person_name", normalized_name, full_name)
    - ("address", normalized_address, raw_address)
    """
    safe_depth = max(0, min(int(depth or 0), MAX_DEPTH))
    seed_icos = [clean_ico(ico) for ico in seed_icos if clean_ico(ico)]

    # Inicializuj frontu s počáteční IČO
    queue: deque[tuple[str, str, int, str | None]] = deque(
        (("company_ico", ico, 0, None) for ico in seed_icos)
    )

    seen_icos: set[str] = set()
    seen_people: set[str] = set()
    seen_addresses: set[str] = set()

    seed_counts: dict[str, int] = {ico: 0 for ico in seed_icos}
    records: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    warnings: list[str] = []

    # Diagnostika
    diagnostics_data = {
        "processed_companies": 0,
        "processed_people": 0,
        "processed_addresses": 0,
        "queued_companies": len(seed_icos),
        "queued_people": 0,
        "queued_addresses": 0,
        "resolved_candidate_companies": 0,
        "unresolved_candidate_companies": 0,
        "skipped_duplicates": 0,
        "skipped_low_confidence": 0,
        "source_failures": 0,
    }

    while queue and len(seen_icos) < MAX_TOTAL_ENTITIES:
        queue_type, queue_value, level, queue_meta = queue.popleft()

        if queue_type == "company_ico":
            ico = queue_value
            if ico in seen_icos:
                diagnostics_data["skipped_duplicates"] += 1
                continue
            seen_icos.add(ico)
            diagnostics_data["processed_companies"] += 1

            try:
                source_data = fetch_company_data(
                    ico,
                    include_historical=include_historical,
                    include_public_aggregators=include_external,
                    force_refresh=force_refresh,
                )
                record = calculate_risk_signals(normalize_entities(source_data))
                records.append(record)

                # Vytvoř hranu
                if level > 0:
                    parent_ico = queue_meta
                    edges.append({
                        "source_ico": parent_ico,
                        "target_ico": ico,
                        "level": level,
                        "relation_type": "navázaná firma",
                        "source_name": None,
                        "source_url": None,
                        "confidence": "verified",
                        "verification_status": "verified_primary",
                        "is_historical": False,
                    })
            except Exception as exc:
                warnings.append(f"Chyba při načítání IČO {ico}: {exc}")
                diagnostics_data["source_failures"] += 1
                continue

        elif queue_type == "company_name":
            company_name = queue_value
            if company_name in seen_people:  # Opakované jméno
                diagnostics_data["skipped_duplicates"] += 1
                continue
            seen_people.add(company_name)

            # Hledej kandidáty podle názvu
            candidates = _search_companies_by_name(company_name)
            if candidates:
                diagnostics_data["resolved_candidate_companies"] += len(candidates)
                for candidate in candidates:
                    candidate_ico = candidate.get("ico")
                    if candidate_ico not in seen_icos:
                        if level < safe_depth:
                            queue.append((
                                "company_ico",
                                candidate_ico,
                                level + 1,
                                queue_meta,
                            ))
                            diagnostics_data["queued_companies"] += 1
            else:
                diagnostics_data["unresolved_candidate_companies"] += 1
                warnings.append(
                    f"Kandidátní firma '{company_name}' se nepodařilo vyřešit na IČO."
                )

        elif queue_type == "person_name":
            person_normalized = queue_value
            person_full = queue_meta  # queue_meta obsahuje full name
            if person_normalized in seen_people:
                diagnostics_data["skipped_duplicates"] += 1
                continue
            seen_people.add(person_normalized)
            diagnostics_data["processed_people"] += 1

            # Hledej firmy, kde se osoba objevuje
            candidates = _search_companies_by_person_name(person_full or person_normalized)
            if candidates:
                diagnostics_data["resolved_candidate_companies"] += len(candidates)
                for candidate in candidates:
                    candidate_ico = candidate.get("ico")
                    if candidate_ico not in seen_icos:
                        if level < safe_depth:
                            queue.append((
                                "company_ico",
                                candidate_ico,
                                level + 1,
                                queue_meta,
                            ))
                            diagnostics_data["queued_companies"] += 1
                            edges.append({
                                "source_ico": queue_meta if level > 0 else None,
                                "target_ico": candidate_ico,
                                "level": level + 1,
                                "relation_type": f"osoba: {person_full or person_normalized}",
                                "source_name": candidate.get("source_name"),
                                "source_url": candidate.get("source_url"),
                                "confidence": candidate.get("confidence", "low"),
                                "verification_status": candidate.get("verification_status", "candidate_needs_resolution"),
                                "is_historical": False,
                            })

        elif queue_type == "address":
            address_normalized = queue_value
            address_raw = queue_meta
            if address_normalized in seen_addresses:
                diagnostics_data["skipped_duplicates"] += 1
                continue
            seen_addresses.add(address_normalized)
            diagnostics_data["processed_addresses"] += 1

            # Hledej firmy na stejné adrese
            candidates = _search_companies_by_address(address_raw or address_normalized)
            if candidates:
                diagnostics_data["resolved_candidate_companies"] += len(candidates)
                for candidate in candidates:
                    candidate_ico = candidate.get("ico")
                    if candidate_ico not in seen_icos:
                        if level < safe_depth:
                            queue.append((
                                "company_ico",
                                candidate_ico,
                                level + 1,
                                queue_meta,
                            ))
                            diagnostics_data["queued_companies"] += 1
                            edges.append({
                                "source_ico": queue_meta if level > 0 else None,
                                "target_ico": candidate_ico,
                                "level": level + 1,
                                "relation_type": f"adresa: {address_raw}",
                                "source_name": candidate.get("source_name"),
                                "source_url": candidate.get("source_url"),
                                "confidence": candidate.get("confidence", "low"),
                                "verification_status": candidate.get("verification_status", "candidate_needs_resolution"),
                                "is_historical": False,
                            })

        # Zpracuj targety z aktuálního záznamu
        if queue_type == "company_ico" and level < safe_depth:
            record = next((r for r in records if r.get("ico") == queue_value), None)
            if record:
                seed = queue_value
                targets = collect_expansion_targets(
                    record,
                    include_external=include_external,
                    include_person_expansion=include_person_expansion,
                    include_address_expansion=include_address_expansion,
                )

                for target in targets:
                    if seed_counts.get(seed, 0) >= MAX_NEW_COMPANIES_PER_SEED:
                        warnings.append(
                            f"U IČO {seed} byl dosažen limit {MAX_NEW_COMPANIES_PER_SEED} nových firem."
                        )
                        break

                    target_type = target.get("target_type")
                    target_value = target.get("value")

                    if target_type == "company":
                        if target.get("is_name_search"):
                            if target_value not in seen_people:
                                queue.append((
                                    "company_name",
                                    target_value,
                                    level + 1,
                                    seed,
                                ))
                                diagnostics_data["queued_companies"] += 1
                                seed_counts[seed] = seed_counts.get(seed, 0) + 1
                        else:
                            if target_value not in seen_icos:
                                queue.append((
                                    "company_ico",
                                    target_value,
                                    level + 1,
                                    seed,
                                ))
                                diagnostics_data["queued_companies"] += 1
                                seed_counts[seed] = seed_counts.get(seed, 0) + 1

                    elif target_type == "person":
                        if target_value not in seen_people:
                            queue.append((
                                "person_name",
                                target_value,
                                level + 1,
                                target.get("person_full_name"),
                            ))
                            diagnostics_data["queued_people"] += 1

                    elif target_type == "address":
                        if target_value not in seen_addresses:
                            queue.append((
                                "address",
                                target_value,
                                level + 1,
                                target.get("raw_address"),
                            ))
                            diagnostics_data["queued_addresses"] += 1

    if queue:
        warnings.append(
            f"Síť byla zkrácena po dosažení limitu {MAX_TOTAL_ENTITIES} subjektů."
        )

    return {
        "records": records,
        "edges": edges,
        "diagnostics": {
            "seed_icos": len(seed_icos),
            "processed_companies": diagnostics_data["processed_companies"],
            "processed_people": diagnostics_data["processed_people"],
            "processed_addresses": diagnostics_data["processed_addresses"],
            "queued_companies": diagnostics_data["queued_companies"],
            "queued_people": diagnostics_data["queued_people"],
            "queued_addresses": diagnostics_data["queued_addresses"],
            "resolved_candidate_companies": diagnostics_data["resolved_candidate_companies"],
            "unresolved_candidate_companies": diagnostics_data["unresolved_candidate_companies"],
            "skipped_duplicates": diagnostics_data["skipped_duplicates"],
            "skipped_low_confidence": diagnostics_data["skipped_low_confidence"],
            "source_failures": diagnostics_data["source_failures"],
            "depth": safe_depth,
            "include_external": include_external,
            "include_person_expansion": include_person_expansion,
            "include_address_expansion": include_address_expansion,
            "max_new_companies_per_seed": MAX_NEW_COMPANIES_PER_SEED,
            "max_total_entities": MAX_TOTAL_ENTITIES,
        },
        "warnings": sorted(set(warnings)),
    }
