"""Komponenty vstupů a úvodních bloků aplikace."""

from typing import Any

import streamlit as st

DEFAULT_SESSION_STATE: dict[str, Any] = {
    "input_text": "",
    "relationship_scope": "Jen aktuální",
    "expansion_depth": 1,
    "auto_include_all_entities_initial": False,
    "results": [],
    "last_analysis_summary": None,
    "selected_relationship_people_names": [],
    "selected_relationship_people_rows": [],
    "relationship_include_all_entities": False,
    "cross_analysis_people": [],
    "cross_analysis_enabled": False,
    "cross_people_text": "",
    "cross_ico_text": "",
    "extra_relationship_ico_text": "",
    "auto_include_all_entities_extra": False,
    "compare_all_entities_global": False,
    "pending_select_all_entities": False,
    "current_screen": "📊 Přehled",
}


def initialize_session_state(persisted_state: dict[str, Any]) -> None:
    for key, default_value in DEFAULT_SESSION_STATE.items():
        if key not in st.session_state:
            st.session_state[key] = persisted_state.get(key, default_value)


def render_header() -> None:
    st.markdown(
        """
        <style>
        .firmograf-hero {padding: 0.25rem 0 0.5rem 0;}
        .firmograf-kicker {font-size: 2rem; font-weight: 700; color: #1E3A5F; line-height: 1.1; margin: 0;}
        .firmograf-subtitle {font-size: 1rem; font-weight: 600; color: #2563EB; margin: 0.15rem 0 0.35rem 0;}
        .firmograf-copy {font-size: 1rem; color: #334155; margin: 0;}
        @media (max-width: 640px) {
          .firmograf-kicker {font-size: 1.65rem;}
          .firmograf-subtitle {font-size: 0.95rem;}
          .firmograf-copy {font-size: 0.95rem;}
        }
        </style>
        <div class="firmograf-hero">
          <div class="firmograf-kicker">🔗 Firmograf</div>
          <div class="firmograf-subtitle">Analýza firemních vazeb a propojení</div>
          <div class="firmograf-copy">Objevte vazby mezi firmami, osobami a adresami během několika sekund.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_app_navigation(results: list[dict[str, Any]]) -> str:
    with st.sidebar:
        st.markdown("## Firmograf")
        current_screen = st.radio(
            "Navigace",
            options=["📊 Přehled", "🏢 Firmy", "👤 Osoby", "🕸 Vazby", "⚠️ Rizika"],
            key="current_screen",
            label_visibility="collapsed",
        )

        st.markdown("### Stav")
        if results:
            total_people = sum(len(record.get("osoby", []) or []) for record in results)
            total_links = sum(len(record.get("navazane_firmy", []) or []) for record in results)
            total_risk = sum(len(record.get("risk_flags", []) or []) for record in results)
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Firmy", len(results))
                st.metric("Osoby", total_people)
            with col2:
                st.metric("Vazby", total_links)
                st.metric("Rizika", total_risk)
        else:
            st.caption("Připraveno k nové analýze")

        if results:
            st.markdown("### Subjekty")
            for record in results[:5]:
                st.caption(f"{record.get('ico')} - {record.get('nazev') or '(bez názvu)'}")
            if len(results) > 5:
                st.caption(f"+ další {len(results) - 5}")

    return current_screen


def render_sources_info() -> None:
    with st.expander("ℹ️ Zdroje a omezení", expanded=False):
        st.markdown(
            """
        - **ARES** – základní údaje o firmě a orgánech.
        - **Registr DPH (ADIS)** – veřejný zdroj pro ověření DPH stavu.
        - **Kurzy.cz** – doplňkové odkazy pro další ruční kontrolu vazeb.
        - **Justice.cz** a **ISIR** – když nejde údaj načíst spolehlivě, aplikace nabídne přímý odkaz.
        - Aplikace si údaje nevymýšlí a neobchází captcha ani přihlášení.
        """
        )


def render_input_controls() -> tuple[str, bool, int, bool, bool]:
    input_text = st.text_area(
        "Zadejte IČO (oddělené čárkou nebo novým řádkem)",
        height=120,
        placeholder="12345678\n87654321",
        key="input_text",
    )

    relationship_scope = st.radio(
        "Zobrazit vazby",
        options=["Jen aktuální", "Aktuální i historické"],
        horizontal=True,
        key="relationship_scope",
        help=(
            "Aktuální vazby ukazují dnes platná propojení. "
            "Historické vazby přidají i dřívější role a spojení z načtených veřejných dat."
        ),
    )
    include_historical = relationship_scope == "Aktuální i historické"
    expansion_depth = st.selectbox(
        "Automatické rozšíření sítě",
        options=[1, 2, 3],
        format_func=lambda value: f"Hloubka {value}",
        key="expansion_depth",
        help=(
            "Hloubka 1 hledá přímo navázané subjekty. "
            "Hloubka 2 přidá navazující firmy o krok dál. "
            "Hloubka 3 prohledá ještě jednu další úroveň."
        ),
    )
    st.caption(
        "Hloubka 1: jen přímo navázané firmy. "
        "Hloubka 2: i firmy navázané na již nalezené subjekty. "
        "Hloubka 3: ještě o jednu úroveň dál pro širší síť vazeb."
    )
    auto_include_all_entities_initial = st.checkbox(
        "Pro vazby osob a firem vyber všechny osoby i firmy spojené s firmou",
        key="auto_include_all_entities_initial",
    )

    col1, _ = st.columns([1, 4])
    with col1:
        run_analysis = st.button("🚀 Spustit analýzu", type="primary", use_container_width=True)

    return (
        input_text,
        include_historical,
        expansion_depth,
        auto_include_all_entities_initial,
        run_analysis,
    )
