"""Spouštění pipeline nad zadanými IČO."""

from typing import Any

import streamlit as st

from analysis.entities import fetch_company_data, normalize_entities
from analysis.risk import calculate_risk_signals


def run_pipeline_for_ico(ico: str, include_historical: bool) -> dict[str, Any]:
    source_data = fetch_company_data(ico, include_historical=include_historical)
    normalized = normalize_entities(source_data)
    return calculate_risk_signals(normalized)


def analyze_icos(
    icos: list[str],
    include_historical: bool,
    replace: bool,
) -> tuple[list[dict[str, Any]], int]:
    existing_results = [] if replace else st.session_state.get("results", [])
    existing_by_ico = {record.get("ico"): record for record in existing_results}
    pending_icos = [ico for ico in icos if replace or ico not in existing_by_ico]

    if not pending_icos and not replace:
        return existing_results, 0

    progress_bar = st.progress(0, text="Připravuji analýzu…")
    status_placeholder = st.empty()
    total_steps = len(pending_icos) if pending_icos else 1

    for index, ico in enumerate(pending_icos):
        status_placeholder.text(f"Zpracovávám IČO {ico}")
        existing_by_ico[ico] = run_pipeline_for_ico(
            ico, include_historical=include_historical
        )
        progress_bar.progress(
            (index + 1) / total_steps,
            text=f"Zpracováno {index + 1}/{total_steps}",
        )

    progress_bar.empty()
    status_placeholder.empty()

    ordered_icos = icos if replace else list(existing_by_ico.keys())
    results = [existing_by_ico[ico] for ico in ordered_icos if ico in existing_by_ico]
    st.session_state["results"] = results
    return results, len(pending_icos)
