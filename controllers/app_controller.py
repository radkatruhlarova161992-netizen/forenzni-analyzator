"""Hlavní controller aplikace."""

import streamlit as st

from controllers.actions import (
    apply_pending_select_all_entities,
    handle_initial_analysis,
    handle_ui_actions,
    reset_current_case,
)
from controllers.maintenance import refresh_cached_subjects_if_due
from controllers.payloads import build_ui_payloads
from core.database import initialize_database
from core.state import save_persisted_state
from ui.render_ui import render_ui


def persist_state() -> None:
    save_persisted_state(
        {
            "input_text": st.session_state.get("input_text", ""),
            "relationship_scope": st.session_state.get(
                "relationship_scope", "Jen aktuální"
            ),
            "expansion_depth": st.session_state.get("expansion_depth", 1),
            "auto_include_all_entities_initial": st.session_state.get(
                "auto_include_all_entities_initial", False
            ),
            "include_public_aggregators": st.session_state.get(
                "include_public_aggregators", False
            ),
            "results": st.session_state.get("results", []),
            "last_analysis_summary": st.session_state.get(
                "last_analysis_summary", None
            ),
            "selected_relationship_people_names": st.session_state.get(
                "selected_relationship_people_names", []
            ),
            "selected_relationship_people_rows": st.session_state.get(
                "selected_relationship_people_rows", []
            ),
            "relationship_include_all_entities": st.session_state.get(
                "relationship_include_all_entities", False
            ),
            "cross_analysis_people": st.session_state.get("cross_analysis_people", []),
            "cross_analysis_enabled": st.session_state.get(
                "cross_analysis_enabled", False
            ),
            "cross_people_text": st.session_state.get("cross_people_text", ""),
            "cross_ico_text": st.session_state.get("cross_ico_text", ""),
            "extra_relationship_ico_text": st.session_state.get(
                "extra_relationship_ico_text", ""
            ),
            "auto_include_all_entities_extra": st.session_state.get(
                "auto_include_all_entities_extra", False
            ),
            "compare_all_entities_global": st.session_state.get(
                "compare_all_entities_global", False
            ),
            "pending_select_all_entities": st.session_state.get(
                "pending_select_all_entities", False
            ),
        }
    )


def run_app_controller(current_screen: str) -> None:
    initialize_database()
    refresh_cached_subjects_if_due()

    if st.session_state.get("request_reset_case"):
        reset_current_case()
        persist_state()
        st.rerun()

    include_historical = (
        st.session_state.get("relationship_scope") == "Aktuální i historické"
    )

    results = st.session_state.get("results", [])
    apply_pending_select_all_entities(results)

    payloads = build_ui_payloads(
        results=results,
        selected_people_names=st.session_state.get(
            "selected_relationship_people_names", []
        ),
        selected_people_rows=st.session_state.get(
            "selected_relationship_people_rows", []
        ),
        relationship_include_all_entities=st.session_state.get(
            "relationship_include_all_entities", False
        ),
        cross_analysis_people=st.session_state.get("cross_analysis_people", []),
        cross_analysis_enabled=st.session_state.get("cross_analysis_enabled", False),
    )

    actions = render_ui(
        current_screen,
        results,
        include_historical,
        st.session_state.get("relationship_scope", "Jen aktuální"),
        payloads["relationship_graph"],
        payloads["cross_analysis_payload"],
        payloads["selected_people_payload"],
    )

    if actions["run_analysis"]:
        handle_initial_analysis(
            actions["input_text"],
            actions["include_historical"],
            actions["expansion_depth"],
            actions["auto_include_all_entities_initial"],
            actions["include_public_aggregators"],
            force_refresh=False,
        )
        persist_state()
        st.rerun()

    if actions.get("refresh_data"):
        current_icos = [record.get("ico") for record in results if record.get("ico")]
        handle_initial_analysis(
            actions["input_text"],
            actions["include_historical"],
            actions["expansion_depth"],
            actions["auto_include_all_entities_initial"],
            actions["include_public_aggregators"],
            force_refresh=True,
            default_icos=current_icos,
        )
        persist_state()
        st.rerun()

    handle_ui_actions(actions, include_historical, persist_state)
