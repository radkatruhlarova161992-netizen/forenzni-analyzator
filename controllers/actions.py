"""Obsluha UI akcí a práce se session state."""

from collections.abc import Callable
from typing import Any

import streamlit as st

from analysis.graph import collect_all_people_from_records
from controllers.pipeline import analyze_icos
from core.utils import parse_ico_list, parse_person_list


def mark_all_people_checkboxes(
    records: list[dict[str, Any]],
    checked: bool = True,
) -> None:
    for rec in records:
        for person in rec.get("osoby", []) or []:
            person_key = (
                f"{rec.get('ico')}|{person.get('jmeno')}|"
                f"{person.get('role')}|{person.get('od')}|{person.get('do')}"
            )
            st.session_state[f"select_person_{person_key}"] = checked


def apply_pending_select_all_entities(results: list[dict[str, Any]]) -> None:
    if not (st.session_state.get("pending_select_all_entities") and results):
        return

    auto_people_rows = collect_all_people_from_records(results)
    mark_all_people_checkboxes(results, checked=True)
    st.session_state["selected_relationship_people_rows"] = auto_people_rows
    st.session_state["selected_relationship_people_names"] = sorted(
        {person["jmeno"] for person in auto_people_rows}
    )
    st.session_state["relationship_include_all_entities"] = True
    st.session_state["pending_select_all_entities"] = False


def handle_initial_analysis(
    input_text: str,
    include_historical: bool,
    auto_include_all_entities_initial: bool,
) -> None:
    icos = parse_ico_list(input_text)
    if not icos:
        st.warning("Nezadal jsi žádné platné IČO.")
        return

    st.session_state["selected_relationship_people_names"] = []
    st.session_state["selected_relationship_people_rows"] = []
    updated_results, _ = analyze_icos(
        icos,
        include_historical=include_historical,
        replace=True,
    )
    st.session_state["relationship_include_all_entities"] = (
        auto_include_all_entities_initial
    )
    if auto_include_all_entities_initial:
        auto_people_rows = collect_all_people_from_records(updated_results)
        mark_all_people_checkboxes(updated_results, checked=True)
        st.session_state["selected_relationship_people_rows"] = auto_people_rows
        st.session_state["selected_relationship_people_names"] = sorted(
            {person["jmeno"] for person in auto_people_rows}
        )
    st.success(f"Analýza dokončena pro {len(icos)} IČO.")


def handle_ui_actions(
    actions: dict[str, Any],
    include_historical: bool,
    persist_callback: Callable[[], None],
) -> None:
    results = st.session_state.get("results", [])

    if actions["compare_all_entities"] and results:
        st.session_state["pending_select_all_entities"] = True
        persist_callback()
        st.rerun()

    if actions["run_cross_analysis"]:
        cross_people = parse_person_list(actions["cross_people_text"])
        cross_icos = parse_ico_list(actions["cross_ico_text"])
        if cross_icos:
            updated_results, added_count = analyze_icos(
                cross_icos,
                include_historical=include_historical,
                replace=False,
            )
            if added_count:
                st.success(
                    f"Pro rozšířenou analýzu bylo doplněno {added_count} dalších firem."
                )
            results = updated_results
        st.session_state["cross_analysis_people"] = cross_people
        st.session_state["cross_analysis_enabled"] = True
        persist_callback()
        st.rerun()

    if actions["run_selected_people_relationships"]:
        st.session_state["selected_relationship_people_names"] = sorted(
            {person["jmeno"] for person in actions["selected_people"]}
        )
        st.session_state["selected_relationship_people_rows"] = actions["selected_people"]
        st.session_state["relationship_include_all_entities"] = False
        persist_callback()
        st.rerun()

    if actions["add_relationship_companies"]:
        extra_icos = parse_ico_list(actions["extra_ico_text"])
        if not extra_icos:
            st.warning("Nezadal jsi žádné platné IČO pro rozšíření vztahů.")
            return

        updated_results, added_count = analyze_icos(
            extra_icos,
            include_historical=include_historical,
            replace=False,
        )
        if added_count == 0:
            st.info("Všechna zadaná IČA už v analýze jsou.")
        else:
            st.success(
                f"Do porovnání vztahů bylo přidáno {added_count} nových firem. "
                f"Celkem je teď načteno {len(updated_results)} firem."
            )
        if actions["auto_include_all_entities_extra"]:
            st.session_state["pending_select_all_entities"] = True
        persist_callback()
        st.rerun()
