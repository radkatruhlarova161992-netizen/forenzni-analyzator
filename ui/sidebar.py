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
    "graph_selected_node_id": None,
    "graph_zoom_level": 1.0,
    "graph_show_companies": True,
    "graph_show_people": True,
    "graph_show_addresses": True,
    "graph_show_historical": True,
    "graph_show_risks": True,
    "confirm_reset_case": False,
    "request_reset_case": False,
}

EXPANSION_DEPTH_LABELS = {
    1: "Přímé vazby",
    2: "Rozšířené vazby",
    3: "Kompletní síť",
}

EXPANSION_DEPTH_DESCRIPTIONS = {
    1: "Analyzuje pouze zadaný subjekt a jeho přímé osoby, adresy a rizika.",
    2: "Analyzuje zadaný subjekt, dohledává další firmy nalezených osob a ukazuje společné osoby a adresy.",
    3: "Pokračuje i přes další nalezené firmy a vytváří víceúrovňovou síť pro odhalení nepřímých vazeb.",
}


def initialize_session_state(persisted_state: dict[str, Any]) -> None:
    for key, default_value in DEFAULT_SESSION_STATE.items():
        if key not in st.session_state:
            st.session_state[key] = persisted_state.get(key, default_value)


def render_header() -> None:
    st.markdown(
        """
        <style>
        .connexa-topbar {
            display:flex;
            align-items:center;
            justify-content:space-between;
            gap:1rem;
            padding:0.15rem 0 1.05rem 0;
        }
        .connexa-brand {
            display:flex;
            align-items:center;
            gap:0.65rem;
            color:#06143A;
            font-size:1.55rem;
            font-weight:800;
            letter-spacing:0;
        }
        .connexa-logo-mark {
            width:34px;
            height:34px;
            display:grid;
            place-items:center;
            color:#2F5BFF;
            position:relative;
        }
        .connexa-logo-mark:before,
        .connexa-logo-mark:after {
            content:"";
            position:absolute;
            inset:0;
        }
        .connexa-logo-mark:before {
            width:16px;
            height:16px;
            border:2px solid #2F5BFF;
            transform:rotate(45deg);
            top:9px;
            left:9px;
            border-radius:4px;
            background:#fff;
        }
        .connexa-logo-mark:after {
            background:
              radial-gradient(circle, #2F5BFF 0 4px, transparent 4.5px) 50% 0/10px 10px no-repeat,
              radial-gradient(circle, #2F5BFF 0 4px, transparent 4.5px) 100% 50%/10px 10px no-repeat,
              radial-gradient(circle, #2F5BFF 0 4px, transparent 4.5px) 50% 100%/10px 10px no-repeat,
              radial-gradient(circle, #2F5BFF 0 4px, transparent 4.5px) 0 50%/10px 10px no-repeat;
        }
        .connexa-nav {
            display:flex;
            align-items:center;
            gap:3rem;
            color:#06143A;
            font-size:0.92rem;
            font-weight:700;
            white-space:nowrap;
        }
        .connexa-login {
            display:flex;
            align-items:center;
            gap:0.6rem;
            color:#06143A;
            font-size:0.95rem;
            font-weight:700;
            white-space:nowrap;
        }
        .connexa-login-icon {
            font-size:1.1rem;
        }
        @media (max-width: 640px) {
            .connexa-brand {font-size:1.35rem;}
            .connexa-nav {display:none;}
        }
        @media (max-width: 900px) {
            .connexa-nav {gap:1.5rem; font-size:0.88rem;}
        }
        </style>
        <div class="connexa-topbar">
          <div class="connexa-brand"><span class="connexa-logo-mark"></span><span>Connexa</span></div>
          <div class="connexa-nav">
            <span>Jak to funguje</span>
            <span>Funkce</span>
            <span>Ceník</span>
            <span>O nás</span>
            <span>Blog</span>
          </div>
          <div class="connexa-login"><span class="connexa-login-icon">◔</span><span>Přihlásit se</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_app_navigation(results: list[dict[str, Any]]) -> str:
    with st.sidebar:
        st.markdown("## Connexa")
        current_screen = st.radio(
            "Navigace",
            options=["📊 Přehled", "🏢 Firmy", "👤 Osoby", "🕸 Vazby", "🔗 Graf vazeb", "⚠️ Rizika"],
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

        render_new_case_action("sidebar")

        if results:
            st.markdown("### Subjekty")
            for record in results[:5]:
                st.caption(f"{record.get('ico')} - {record.get('nazev') or '(bez názvu)'}")
            if len(results) > 5:
                st.caption(f"+ další {len(results) - 5}")

    return current_screen


def render_new_case_action(section_key: str) -> None:
    if st.button("🧹 Nový případ", key=f"new_case_button_{section_key}", use_container_width=True):
        st.session_state["confirm_reset_case"] = True

    if not st.session_state.get("confirm_reset_case"):
        return

    st.warning("Opravdu chcete smazat aktuální analýzu a začít nový případ?")
    col1, col2 = st.columns(2)
    with col1:
        if st.button(
            "Ano, smazat",
            key=f"confirm_reset_case_{section_key}",
            use_container_width=True,
            type="primary",
        ):
            st.session_state["request_reset_case"] = True
            st.session_state["confirm_reset_case"] = False
    with col2:
        if st.button(
            "Zrušit",
            key=f"cancel_reset_case_{section_key}",
            use_container_width=True,
        ):
            st.session_state["confirm_reset_case"] = False
            st.rerun()


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


def render_input_controls(
    *,
    homepage_mode: bool = False,
) -> tuple[str, bool, int, bool, bool, bool]:
    if homepage_mode:
        search_col, action_col = st.columns([3.9, 1.7], gap="small")
        with search_col:
            input_text = st.text_area(
                "Zadejte IČO, název firmy nebo jméno osoby",
                height=74,
                placeholder="Zadejte IČO, název firmy nebo jméno osoby",
                key="input_text",
                label_visibility="collapsed",
            )
        with action_col:
            st.markdown("<div style='height:2px'></div>", unsafe_allow_html=True)
            run_analysis = st.button("Analyzovat →", type="primary", use_container_width=True)

        with st.expander("Upřesnit analýzu", expanded=False):
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
                "Rozsah analýzy",
                options=[1, 2, 3],
                format_func=lambda value: EXPANSION_DEPTH_LABELS[value],
                key="expansion_depth",
                help=(
                    "Vyberte, jak daleko má Connexa pokračovat při dohledávání dalších firem a vazeb."
                ),
            )
            st.caption(
                f"**{EXPANSION_DEPTH_LABELS[expansion_depth]}**: "
                f"{EXPANSION_DEPTH_DESCRIPTIONS[expansion_depth]}"
            )
            auto_include_all_entities_initial = st.checkbox(
                "Pro vazby osob a firem vyber všechny osoby i firmy spojené s firmou",
                key="auto_include_all_entities_initial",
            )
            refresh_data = st.button("Aktualizovat data", use_container_width=True)
    else:
        input_text = st.text_area(
            "IČO k analýze",
            height=96,
            placeholder="Vložte IČO, více hodnot oddělte čárkou nebo novým řádkem",
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
            "Rozsah analýzy",
            options=[1, 2, 3],
            format_func=lambda value: EXPANSION_DEPTH_LABELS[value],
            key="expansion_depth",
            help=(
                "Vyberte, jak daleko má Connexa pokračovat při dohledávání dalších firem a vazeb."
            ),
        )
        st.caption(
            f"**{EXPANSION_DEPTH_LABELS[expansion_depth]}**: "
            f"{EXPANSION_DEPTH_DESCRIPTIONS[expansion_depth]}"
        )
        auto_include_all_entities_initial = st.checkbox(
            "Pro vazby osob a firem vyber všechny osoby i firmy spojené s firmou",
            key="auto_include_all_entities_initial",
        )

        col1, col2, _ = st.columns([1, 1, 3])
        with col1:
            run_analysis = st.button("Spustit analýzu", type="primary", use_container_width=True)
        with col2:
            refresh_data = st.button("Aktualizovat data", use_container_width=True)

    return (
        input_text,
        include_historical,
        expansion_depth,
        auto_include_all_entities_initial,
        run_analysis,
        refresh_data,
    )
