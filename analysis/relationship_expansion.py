"""Rizene rozsireni site vztahu bez vazby na Streamlit UI."""

from __future__ import annotations

from collections import deque
from typing import Any

from analysis.entities import fetch_company_data, normalize_entities
from analysis.risk import calculate_risk_signals
from core.utils import clean_ico

MAX_NEW_COMPANIES_PER_SEED = 150
MAX_TOTAL_ENTITIES = 1000
MAX_DEPTH = 3


def collect_related_icos(record: dict[str, Any], include_external: bool) -> list[str]:
    related: list[str] = []
    for company in record.get("navazane_firmy", []) or []:
        if not include_external and company.get("verification_status") == "unverified_external":
            continue
        ico = clean_ico(str(company.get("ico") or ""))
        if ico and ico != record.get("ico") and ico not in related:
            related.append(ico)
    return related


def expand_relationship_network(
    seed_icos: list[str],
    depth: int,
    include_external: bool,
    include_historical: bool = False,
    force_refresh: bool = False,
) -> dict[str, Any]:
    """Načte viceurovnovou sit s deduplikaci a ochrannymi limity."""
    safe_depth = max(0, min(int(depth or 0), MAX_DEPTH))
    seed_icos = [clean_ico(ico) for ico in seed_icos if clean_ico(ico)]
    queue: deque[tuple[str, int, str | None]] = deque((ico, 0, None) for ico in seed_icos)
    seen_icos: set[str] = set()
    seed_counts: dict[str, int] = {ico: 0 for ico in seed_icos}
    records: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    warnings: list[str] = []

    while queue and len(seen_icos) < MAX_TOTAL_ENTITIES:
        ico, level, parent_ico = queue.popleft()
        if ico in seen_icos:
            continue
        seen_icos.add(ico)

        source_data = fetch_company_data(
            ico,
            include_historical=include_historical,
            include_public_aggregators=include_external,
            force_refresh=force_refresh,
        )
        record = calculate_risk_signals(normalize_entities(source_data))
        records.append(record)
        if parent_ico:
            edges.append({"source_ico": parent_ico, "target_ico": ico, "level": level})

        if level >= safe_depth:
            continue

        seed = parent_ico or ico
        for related_ico in collect_related_icos(record, include_external):
            if related_ico in seen_icos:
                continue
            if seed_counts.get(seed, 0) >= MAX_NEW_COMPANIES_PER_SEED:
                warnings.append(
                    f"U IČO {seed} byl dosažen limit {MAX_NEW_COMPANIES_PER_SEED} nových firem."
                )
                break
            seed_counts[seed] = seed_counts.get(seed, 0) + 1
            queue.append((related_ico, level + 1, ico))

    if queue:
        warnings.append(
            f"Síť byla zkrácena po dosažení limitu {MAX_TOTAL_ENTITIES} subjektů."
        )

    return {
        "records": records,
        "edges": edges,
        "diagnostics": {
            "seed_icos": len(seed_icos),
            "processed_companies": len(records),
            "depth": safe_depth,
            "include_external": include_external,
            "max_new_companies_per_seed": MAX_NEW_COMPANIES_PER_SEED,
            "max_total_entities": MAX_TOTAL_ENTITIES,
        },
        "warnings": sorted(set(warnings)),
    }
