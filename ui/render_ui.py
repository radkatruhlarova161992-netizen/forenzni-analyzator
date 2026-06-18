"""Hlavní skládání produktových obrazovek bez fetchování a bez analýzy."""

from typing import Any

import streamlit as st

from ui.company_detail import render_companies_screen, render_people_screen
from ui.relationships import render_intersections_screen, render_relationships_screen
from ui.risk_report import render_case_screen, render_risk_signals_screen


def render_ui(
    current_screen: str,
    results: list[dict[str, Any]],
    include_historical: bool,
    relationship_scope: str,
    relationship_graph: dict[str, Any] | None,
    cross_analysis_payload: dict[str, Any] | None,
    selected_people_payload: dict[str, Any] | None,
) -> dict[str, Any]:
    actions: dict[str, Any] = {
        "compare_all_entities": False,
        "run_analysis": False,
        "input_text": "",
        "include_historical": False,
        "auto_include_all_entities_initial": False,
        "run_cross_analysis": False,
        "cross_people_text": "",
        "cross_ico_text": "",
        "selected_people": [],
        "run_selected_people_relationships": False,
        "extra_ico_text": "",
        "auto_include_all_entities_extra": False,
        "add_relationship_companies": False,
    }

    if current_screen == "📊 Přehled":
        overview_actions = render_case_screen(results, relationship_scope)
        actions.update(overview_actions)
        return actions

    if not results:
        st.info("Nejprve založ případ a načti alespoň jedno IČO.")
        return actions

    if current_screen == "🏢 Firmy":
        render_companies_screen(results, include_historical)
        return actions

    if current_screen == "👤 Osoby":
        (
            actions["selected_people"],
            actions["run_selected_people_relationships"],
        ) = render_people_screen(results, include_historical)
        return actions

    if current_screen == "🕸 Vazby":
        if relationship_graph and selected_people_payload:
            (
                actions["extra_ico_text"],
                actions["auto_include_all_entities_extra"],
                actions["add_relationship_companies"],
            ) = render_relationships_screen(
                results,
                relationship_graph,
                selected_people_payload["selected_people_names"],
                selected_people_payload["selected_people_rows"],
                selected_people_payload["intersections"],
                selected_people_payload["relationship_include_all_entities"],
                include_historical,
            )
            with st.expander("Rozšířené porovnání", expanded=False):
                (
                    actions["run_cross_analysis"],
                    actions["cross_people_text"],
                    actions["cross_ico_text"],
                ) = render_intersections_screen(cross_analysis_payload)
        else:
            st.info("Nejprve vyber osoby nebo načti firmy, aby bylo možné zobrazit vazby a průniky.")
        return actions

    if current_screen == "⚠️ Rizika":
        render_risk_signals_screen(results)
        return actions

    st.info("Vyber sekci z levého menu.")
    return actions
