"""Spouštění pipeline nad zadanými IČO."""

from collections import deque
from typing import Any

import streamlit as st

from analysis.entities import fetch_company_data, normalize_entities
from analysis.risk import calculate_risk_signals
from core.database import save_company_record
from core.utils import clean_ico


def run_pipeline_for_ico(
    ico: str,
    include_historical: bool,
    include_public_aggregators: bool = False,
    force_refresh: bool = False,
) -> dict[str, Any]:
    source_data = fetch_company_data(
        ico,
        include_historical=include_historical,
        include_public_aggregators=include_public_aggregators,
        force_refresh=force_refresh,
    )
    normalized = normalize_entities(source_data)
    result = calculate_risk_signals(normalized)
    save_company_record(result)
    return result


def collect_related_company_icos(record: dict[str, Any]) -> list[str]:
    related_icos: list[str] = []
    for company in record.get("navazane_firmy", []) or []:
        related_ico = clean_ico(str(company.get("ico") or ""))
        if related_ico and related_ico != record.get("ico") and related_ico not in related_icos:
            related_icos.append(related_ico)
    return related_icos


def analyze_icos(
    icos: list[str],
    include_historical: bool,
    replace: bool,
    expansion_depth: int = 1,
    include_public_aggregators: bool = False,
    force_refresh: bool = False,
) -> tuple[list[dict[str, Any]], int, dict[str, int]]:
    existing_results = [] if replace else st.session_state.get("results", [])
    existing_by_ico = {record.get("ico"): record for record in existing_results}
    seed_icos = [ico for ico in icos if ico]
    pending_seed_icos = [ico for ico in seed_icos if replace or ico not in existing_by_ico]

    if not pending_seed_icos and not replace:
        return existing_results, 0, {
            "requested_companies": len(seed_icos),
            "processed_companies": 0,
            "auto_added_companies": 0,
            "new_people": 0,
        }

    progress_bar = st.progress(0, text="Připravuji analýzu…")
    status_placeholder = st.empty()
    queue: deque[tuple[str, int]] = deque((ico, 0) for ico in pending_seed_icos)
    processed_icos: list[str] = []
    auto_added_icos: list[str] = []
    auto_added_people: set[str] = set()
    seen_queued = set(pending_seed_icos)

    while queue:
        ico, level = queue.popleft()
        status_placeholder.text(
            f"Zpracovávám IČO {ico} (hloubka {level + 1}/{max(expansion_depth, 0) + 1})"
        )
        record = run_pipeline_for_ico(
            ico,
            include_historical=include_historical,
            include_public_aggregators=include_public_aggregators,
            force_refresh=force_refresh,
        )
        existing_by_ico[ico] = record
        processed_icos.append(ico)

        if level > 0:
            auto_added_icos.append(ico)
            auto_added_people.update(
                person.get("jmeno")
                for person in record.get("osoby", []) or []
                if person.get("jmeno")
            )

        if level < expansion_depth:
            for related_ico in collect_related_company_icos(record):
                if related_ico in seen_queued or related_ico in existing_by_ico:
                    continue
                seen_queued.add(related_ico)
                queue.append((related_ico, level + 1))

        current_total = len(processed_icos) + len(queue)
        progress_value = len(processed_icos) / max(current_total, 1)
        progress_bar.progress(
            progress_value,
            text=f"Zpracováno {len(processed_icos)} firem",
        )

    progress_bar.empty()
    status_placeholder.empty()

    ordered_icos = seed_icos if replace else list(existing_by_ico.keys())
    for ico in auto_added_icos:
        if ico not in ordered_icos:
            ordered_icos.append(ico)
    results = [existing_by_ico[ico] for ico in ordered_icos if ico in existing_by_ico]
    st.session_state["results"] = results
    summary = {
        "requested_companies": len(seed_icos),
        "processed_companies": len(processed_icos),
        "auto_added_companies": len(auto_added_icos),
        "new_people": len(auto_added_people),
    }
    return results, len(processed_icos), summary
