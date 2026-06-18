"""UI pro přehled výsledků a rizikových signálů."""

from datetime import datetime
from typing import Any

import pandas as pd
import streamlit as st

from ui.explainers import (
    render_key_findings_intro,
    render_meaning_section,
    render_next_steps_section,
    render_term_tooltips,
)
from ui.sidebar import render_input_controls, render_new_case_action, render_sources_info


def render_case_screen(results: list[dict[str, Any]], relationship_scope: str) -> dict[str, Any]:
    actions = {
        "compare_all_entities": False,
        "input_text": st.session_state.get("input_text", ""),
        "include_historical": st.session_state.get("relationship_scope") == "Aktuální i historické",
        "expansion_depth": st.session_state.get("expansion_depth", 1),
        "auto_include_all_entities_initial": st.session_state.get("auto_include_all_entities_initial", False),
        "include_public_aggregators": st.session_state.get("include_public_aggregators", False),
        "run_analysis": False,
        "refresh_data": False,
        "reset_case": False,
    }

    if results:
        st.subheader("Výsledek analýzy")
        current_ico_block = ", ".join(rec.get("ico") for rec in results if rec.get("ico"))
        if current_ico_block:
            st.caption(f"Zadaná IČA: {current_ico_block}")
        analysis_summary = st.session_state.get("last_analysis_summary") or {}
        if analysis_summary:
            st.info(
                "Nalezeno "
                f"{analysis_summary.get('auto_added_companies', 0)} nových firem a "
                f"{analysis_summary.get('new_people', 0)} nových osob."
            )
        gap_warnings = [
            record.get("external_gap_warning")
            for record in results
            if record.get("external_gap_warning")
        ]
        for warning in gap_warnings[:3]:
            st.warning(warning)
        render_key_findings_intro(results)
        render_dashboard(results)
        with st.expander("Co to znamená?", expanded=True):
            render_meaning_section()
        with st.expander("Doporučené další kroky", expanded=True):
            render_next_steps_section()
        with st.expander("Vysvětlení pojmů", expanded=False):
            render_term_tooltips()
        render_navigation_buttons()
        with st.expander("Podrobnosti a zdroje", expanded=False):
            actions["compare_all_entities"] = render_summary_tab(
                results,
                relationship_scope,
                show_header=False,
            )
            render_sources_info()

        with st.expander("Spustit novou analýzu", expanded=False):
            with st.container(border=True):
                st.markdown("### Nová analýza")
                st.caption("Vlož IČA a spusť analýzu.")
                render_new_case_action("overview_existing")
                (
                    actions["input_text"],
                    actions["include_historical"],
                    actions["expansion_depth"],
                    actions["auto_include_all_entities_initial"],
                    actions["include_public_aggregators"],
                    actions["run_analysis"],
                    actions["refresh_data"],
                ) = render_input_controls()
    else:
        render_landing_sections()
        hero_left, hero_right = st.columns([1.02, 1.08], gap="medium")
        with hero_left:
            render_homepage_intro()
            st.markdown('<div class="connexa-homepage-form">', unsafe_allow_html=True)
            (
                actions["input_text"],
                actions["include_historical"],
                actions["expansion_depth"],
                actions["auto_include_all_entities_initial"],
                actions["include_public_aggregators"],
                actions["run_analysis"],
                actions["refresh_data"],
            ) = render_input_controls(homepage_mode=True)
            st.markdown("</div>", unsafe_allow_html=True)
            st.markdown(
                (
                    '<div class="connexa-home-note">'
                    '<span class="connexa-home-note-icon">⌂</span>'
                    "Pracujeme s veřejnými zdroji dat"
                    "</div>"
                ),
                unsafe_allow_html=True,
            )
        with hero_right:
            render_homepage_network_map()
        render_homepage_sources_band()
        render_homepage_feature_cards()

    return actions


def render_landing_sections() -> None:
    st.markdown(
        """
        <style>
        [data-testid="stSidebar"] {display:none;}
        [data-testid="stSidebarNav"] {display:none;}
        section.main > div.block-container {
            max-width: 1440px;
            padding-top: 0.3rem;
        }
        .connexa-home {
            padding: 0.45rem 0 0.35rem 0;
        }
        .connexa-home-badge {
            display:inline-flex;
            align-items:center;
            gap:0.75rem;
            padding:0.7rem 1rem;
            border-radius:999px;
            background:#F8FBFF;
            color:#344767;
            box-shadow:0 12px 30px rgba(33, 59, 127, 0.06);
            border:1px solid #EEF2FF;
            font-size:0.95rem;
            font-weight:600;
            margin:1.6rem 0 1.35rem;
        }
        .connexa-home-badge-dot {
            width:12px;
            height:12px;
            border-radius:999px;
            background:#2F5BFF;
            box-shadow:0 0 0 7px rgba(47,91,255,.12);
            flex:0 0 auto;
        }
        .connexa-title {
            margin:0;
            color:#06143A;
            font-size:clamp(3rem, 5.6vw, 5.2rem);
            line-height:1.03;
            font-weight:850;
            letter-spacing:0;
            max-width:700px;
        }
        .connexa-title-accent {color:#2F5BFF;}
        .connexa-lead {
            color:#475777;
            font-size:clamp(1.18rem, 1.8vw, 1.42rem);
            line-height:1.55;
            margin:1.3rem 0 1.5rem 0;
            max-width:620px;
        }
        .connexa-home-note {
            display:flex;
            align-items:center;
            gap:0.65rem;
            color:#52617F;
            font-size:1rem;
            margin-top:1rem;
        }
        .connexa-home-note-icon {
            width:22px;
            height:22px;
            border:1px solid #C8D5FF;
            border-radius:999px;
            display:grid;
            place-items:center;
            color:#2F5BFF;
            font-size:0.8rem;
        }
        .connexa-homepage-form [data-testid="stTextArea"] textarea {
            min-height:70px !important;
            border-radius:18px !important;
            border:1px solid #E6ECFA !important;
            font-size:1rem !important;
            padding:1.2rem 1rem 1rem 1rem !important;
            box-shadow:0 12px 28px rgba(15,23,42,.05) !important;
        }
        .connexa-homepage-form [data-testid="stTextArea"] label,
        .connexa-homepage-form [data-testid="stWidgetLabel"] {
            display:none !important;
        }
        .connexa-homepage-form [data-testid="stButton"] > button[kind="primary"] {
            min-height:70px;
            border-radius:18px;
            background:linear-gradient(135deg, #2F5BFF 0%, #3158F6 100%);
            border:0;
            font-size:1rem;
            font-weight:700;
            box-shadow:0 14px 30px rgba(47,91,255,.24);
        }
        .connexa-homepage-form details {
            margin-top:0.7rem;
        }
        .connexa-network-shell {
            position:relative;
            min-height:540px;
            border-radius:32px;
            overflow:hidden;
            background:
              radial-gradient(circle at 50% 50%, rgba(47,91,255,.10), transparent 0 170px),
              radial-gradient(circle at 50% 50%, transparent 0 116px, rgba(47,91,255,.06) 117px 118px, transparent 119px 210px, rgba(47,91,255,.045) 211px 212px, transparent 213px),
              linear-gradient(180deg, #FFFFFF, #FBFCFF);
        }
        .connexa-network-shell:before {
            content:"";
            position:absolute;
            inset:36px;
            background-image:
              radial-gradient(circle at 12% 22%, rgba(47,91,255,.17) 0 3px, transparent 3.5px),
              radial-gradient(circle at 21% 38%, rgba(47,91,255,.12) 0 3px, transparent 3.5px),
              radial-gradient(circle at 35% 13%, rgba(47,91,255,.12) 0 3px, transparent 3.5px),
              radial-gradient(circle at 70% 18%, rgba(47,91,255,.14) 0 3px, transparent 3.5px),
              radial-gradient(circle at 83% 33%, rgba(47,91,255,.12) 0 3px, transparent 3.5px),
              radial-gradient(circle at 79% 73%, rgba(47,91,255,.14) 0 3px, transparent 3.5px),
              radial-gradient(circle at 37% 82%, rgba(47,91,255,.12) 0 3px, transparent 3.5px),
              radial-gradient(circle at 15% 68%, rgba(47,91,255,.14) 0 3px, transparent 3.5px);
            opacity:.95;
        }
        .connexa-network-core {
            position:absolute;
            left:52%;
            top:48%;
            transform:translate(-50%, -50%);
            width:208px;
            height:208px;
            border-radius:999px;
            background:#fff;
            border:1px solid #EEF2FF;
            box-shadow:0 20px 45px rgba(15,23,42,.08);
            display:flex;
            flex-direction:column;
            justify-content:center;
            align-items:center;
            text-align:center;
            z-index:2;
        }
        .connexa-network-core .icon {
            font-size:3rem;
            color:#2F5BFF;
            margin-bottom:0.25rem;
        }
        .connexa-network-core strong {
            color:#12204D;
            font-size:1rem;
        }
        .connexa-network-core span {
            color:#415173;
            font-size:0.92rem;
            margin-top:0.55rem;
        }
        .connexa-network-node {
            position:absolute;
            min-width:188px;
            background:rgba(255,255,255,.95);
            border:1px solid #EEF2FF;
            box-shadow:0 16px 34px rgba(15,23,42,.06);
            border-radius:24px;
            display:flex;
            align-items:center;
            gap:0.8rem;
            padding:1rem 1rem;
            z-index:2;
        }
        .connexa-network-node .node-icon {
            width:44px;
            height:44px;
            border-radius:14px;
            display:grid;
            place-items:center;
            font-size:1.25rem;
            flex:0 0 auto;
        }
        .node-person .node-icon {background:#E9FAF4; color:#1DB974;}
        .node-company .node-icon {background:#F1EDFF; color:#6B46FF;}
        .node-address .node-icon {background:#FFF4E5; color:#FF9800;}
        .node-risk .node-icon {background:#FFF0F0; color:#FF3B30;}
        .connexa-network-node strong {
            display:block;
            color:#12204D;
            font-size:0.95rem;
            line-height:1.15;
        }
        .connexa-network-node span {
            display:block;
            color:#44557C;
            font-size:0.82rem;
            margin-top:0.2rem;
        }
        .connexa-network-line {
            position:absolute;
            height:2px;
            transform-origin:left center;
            z-index:1;
        }
        .line-blue {background:#2F5BFF;}
        .line-teal {background:#0EC5A5;}
        .line-purple {background:#7C4DFF;}
        .line-orange {background:#FF9800;}
        .line-red {background:#FF4B3E;}
        .line-violet {background:#6F45FF;}
        .n1 {left:10%; top:10%;}
        .n2 {right:8%; top:6%;}
        .n3 {right:0%; top:35%;}
        .n4 {left:0%; top:40%;}
        .n5 {left:10%; bottom:12%;}
        .n6 {right:26%; bottom:8%;}
        .n7 {right:2%; bottom:13%;}
        .l1 {left:43%; top:37%; width:92px; transform:rotate(-136deg);}
        .l2 {left:58%; top:33%; width:112px; transform:rotate(-51deg);}
        .l3 {left:64%; top:49%; width:125px; transform:rotate(-12deg);}
        .l4 {left:28%; top:53%; width:100px; transform:rotate(180deg);}
        .l5 {left:41%; top:69%; width:92px; transform:rotate(138deg);}
        .l6 {left:55%; top:70%; width:74px; transform:rotate(86deg);}
        .l7 {left:62%; top:57%; width:137px; transform:rotate(32deg);}
        .connexa-stats-band {
            margin-top:1.6rem;
            border:1px solid #E8EDF8;
            border-radius:18px;
            box-shadow:0 12px 34px rgba(15,23,42,.04);
            background:#fff;
            padding:1.15rem 1.4rem;
        }
        .connexa-stats-grid {
            display:grid;
            grid-template-columns: 1fr 1fr 3fr;
            gap:1rem;
            align-items:center;
        }
        .connexa-stat-pill {
            display:flex;
            align-items:center;
            gap:1rem;
            padding-right:1rem;
            border-right:1px solid #E9EDF5;
        }
        .connexa-stat-pill:last-child {border-right:0;}
        .connexa-stat-bubble {
            width:56px;
            height:56px;
            border-radius:18px;
            background:#F3F6FF;
            display:grid;
            place-items:center;
            font-size:1.6rem;
            color:#2F5BFF;
        }
        .connexa-stat-pill strong {
            display:block;
            color:#12204D;
            font-size:1.05rem;
        }
        .connexa-stat-pill span {
            display:block;
            color:#44557C;
            font-size:0.88rem;
            margin-top:0.15rem;
        }
        .connexa-sources-inline {
            display:flex;
            align-items:center;
            justify-content:space-between;
            gap:1.15rem;
            flex-wrap:wrap;
        }
        .connexa-sources-inline-title {
            color:#52617F;
            font-size:0.96rem;
            min-width:180px;
        }
        .connexa-sources-inline-items {
            display:flex;
            align-items:center;
            gap:2rem;
            flex-wrap:wrap;
            color:#45547A;
            font-size:0.95rem;
            font-weight:700;
        }
        .connexa-features-title {
            text-align:center;
            color:#12204D;
            font-size:1.05rem;
            font-weight:800;
            margin:1.45rem 0 0.95rem;
            letter-spacing:0.02em;
        }
        .connexa-feature-card {
            border:1px solid #E8EDF8;
            border-radius:18px;
            background:#fff;
            box-shadow:0 12px 34px rgba(15,23,42,.04);
            padding:1.6rem 1.4rem;
            min-height:176px;
        }
        .connexa-feature-icon {
            width:72px;
            height:72px;
            border-radius:999px;
            display:grid;
            place-items:center;
            font-size:2rem;
            margin-bottom:1rem;
        }
        .feature-blue {background:#EEF3FF; color:#2F5BFF;}
        .feature-purple {background:#F3EDFF; color:#7C4DFF;}
        .feature-red {background:#FFF0F0; color:#FF4B3E;}
        .feature-green {background:#E8FAF1; color:#14B86A;}
        .connexa-feature-card strong {
            display:block;
            color:#12204D;
            font-size:1.1rem;
            margin-bottom:0.5rem;
        }
        .connexa-feature-card span {
            color:#44557C;
            font-size:0.98rem;
            line-height:1.5;
        }
        .connexa-home-footer {
            text-align:center;
            color:#52617F;
            font-size:1rem;
            margin:1.15rem 0 0.6rem;
        }
        @media (max-width: 1100px) {
            .connexa-stats-grid {grid-template-columns:1fr;}
            .connexa-stat-pill {border-right:0; border-bottom:1px solid #E9EDF5; padding-bottom:0.8rem;}
            .connexa-stat-pill:last-child {border-bottom:0; padding-bottom:0;}
        }
        @media (max-width: 900px) {
            .connexa-network-shell {min-height:500px; margin-top:1rem;}
        }
        @media (max-width: 760px) {
            .connexa-title {font-size:2.8rem;}
            .connexa-lead {font-size:1.06rem;}
            .connexa-network-shell {min-height:640px;}
            .connexa-network-node {min-width:200px;}
            .n1 {left:6%; top:4%;}
            .n2 {right:3%; top:18%;}
            .n3 {right:1%; top:38%;}
            .n4 {left:1%; top:30%;}
            .n5 {left:4%; bottom:20%;}
            .n6 {right:18%; bottom:13%;}
            .n7 {right:2%; bottom:2%;}
            .connexa-network-core {left:52%; top:52%; width:180px; height:180px;}
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_homepage_intro() -> None:
    st.markdown(
        """
        <section class="connexa-home">
          <div class="connexa-home-badge">
            <span class="connexa-home-badge-dot"></span>
            <span>Analýza firemních vazeb a vztahů</span>
          </div>
          <h1 class="connexa-title">Zjistěte, kdo je<br>s kým <span class="connexa-title-accent">propojený.</span></h1>
          <p class="connexa-lead">
            Analyzujte firmy, vlastníky, jednatele a adresy
            z veřejných zdrojů během několika sekund.
          </p>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_homepage_network_map() -> None:
    st.markdown(
        """
        <div class="connexa-network-shell">
          <div class="connexa-network-line line-blue l1"></div>
          <div class="connexa-network-line line-purple l2"></div>
          <div class="connexa-network-line line-teal l3"></div>
          <div class="connexa-network-line line-orange l4"></div>
          <div class="connexa-network-line line-blue l5"></div>
          <div class="connexa-network-line line-violet l6"></div>
          <div class="connexa-network-line line-red l7"></div>

          <div class="connexa-network-node node-person n1">
            <div class="node-icon">👤</div>
            <div><strong>Jan Novák</strong><span>Jednatel</span></div>
          </div>
          <div class="connexa-network-node node-company n2">
            <div class="node-icon">🏢</div>
            <div><strong>ABC Holding a.s.</strong><span>Společnost</span></div>
          </div>
          <div class="connexa-network-node node-person n3">
            <div class="node-icon">👤</div>
            <div><strong>Jiří Veselý</strong><span>Jednatel</span></div>
          </div>
          <div class="connexa-network-node node-address n4">
            <div class="node-icon">📍</div>
            <div><strong>Na Příkopě 123/4</strong><span>110 00 Praha 1<br>Adresa</span></div>
          </div>
          <div class="connexa-network-node node-person n5">
            <div class="node-icon">👤</div>
            <div><strong>Petr Svoboda</strong><span>Společník</span></div>
          </div>
          <div class="connexa-network-node node-company n6">
            <div class="node-icon">🏢</div>
            <div><strong>123 Import s.r.o.</strong><span>Společnost</span></div>
          </div>
          <div class="connexa-network-node node-risk n7">
            <div class="node-icon">!</div>
            <div><strong>Rizikový signál</strong><span>Insolvence v minulosti</span></div>
          </div>

          <div class="connexa-network-core">
            <div class="icon">🏢</div>
            <strong>DEMO COMPANY s.r.o.</strong>
            <span>IČO: 123 45 678</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_homepage_sources_band() -> None:
    st.markdown(
        """
        <div class="connexa-stats-band">
          <div class="connexa-stats-grid">
            <div class="connexa-stat-pill">
              <div class="connexa-stat-bubble">🏢</div>
              <div><strong>3,2 mil.</strong><span>firem</span></div>
            </div>
            <div class="connexa-stat-pill">
              <div class="connexa-stat-bubble">🔗</div>
              <div><strong>85 mil.</strong><span>vazeb</span></div>
            </div>
            <div class="connexa-sources-inline">
              <div class="connexa-sources-inline-title">Pracujeme s veřejnými zdroji</div>
              <div class="connexa-sources-inline-items">
                <span>ARES</span>
                <span>OR</span>
                <span>RŽP</span>
                <span>ČÚZK</span>
                <span>Justice.cz</span>
                <span>a další</span>
              </div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_homepage_feature_cards() -> None:
    st.markdown('<div class="connexa-features-title">CO UMÍ CONNEXA</div>', unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns(4, gap="medium")
    with col1:
        st.markdown(
            (
                '<div class="connexa-feature-card">'
                '<div class="connexa-feature-icon feature-blue">⌕</div>'
                "<strong>Vyhledání firmy</strong>"
                "<span>Rychle najděte firmu podle IČO, názvu nebo osoby.</span>"
                "</div>"
            ),
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            (
                '<div class="connexa-feature-card">'
                '<div class="connexa-feature-icon feature-purple">⌘</div>'
                "<strong>Analýza vazeb</strong>"
                "<span>Zobrazíme propojení mezi firmami, osobami a adresami.</span>"
                "</div>"
            ),
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            (
                '<div class="connexa-feature-card">'
                '<div class="connexa-feature-icon feature-red">!</div>'
                "<strong>Rizikové signály</strong>"
                "<span>Upozorníme na rizikové signály z veřejných zdrojů.</span>"
                "</div>"
            ),
            unsafe_allow_html=True,
        )
    with col4:
        st.markdown(
            (
                '<div class="connexa-feature-card">'
                '<div class="connexa-feature-icon feature-green">◔</div>'
                "<strong>Historické změny</strong>"
                "<span>Sledujte vývoj vztahů a změny v čase.</span>"
                "</div>"
            ),
            unsafe_allow_html=True,
        )
    st.markdown(
        '<div class="connexa-home-footer">⌂ Bezpečně. Spolehlivě. V souladu s GDPR.</div>',
        unsafe_allow_html=True,
    )


def render_dashboard(results: list[dict[str, Any]]) -> None:
    total_companies = len(results)
    total_people = sum(len(record.get("osoby", []) or []) for record in results)
    total_relationships = (
        sum(len(record.get("osoby", []) or []) for record in results)
        + sum(len(record.get("navazane_firmy", []) or []) for record in results)
    )
    total_risks = sum(len(record.get("risk_flags", []) or []) for record in results)

    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
    with metric_col1:
        with st.container(border=True):
            st.metric("Firmy", total_companies)
    with metric_col2:
        with st.container(border=True):
            st.metric("Osoby", total_people)
    with metric_col3:
        with st.container(border=True):
            st.metric("Vazby", total_relationships)
    with metric_col4:
        with st.container(border=True):
            st.metric("Rizika", total_risks)

    st.markdown("### Přehled")
    findings = build_top_findings(results)
    if not findings:
        st.info("Zatím tu není žádný výrazný průnik nebo signál.")
        return

    for finding in findings:
        with st.container(border=True):
            st.markdown(f"**{finding['title']}**")
            st.caption(finding["detail"])


def render_navigation_buttons() -> None:
    st.markdown("### Kam dál")
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        if st.button("🏢 Zobrazit firmy", use_container_width=True):
            st.session_state["current_screen"] = "🏢 Firmy"
            st.rerun()
    with col2:
        if st.button("👤 Zobrazit osoby", use_container_width=True):
            st.session_state["current_screen"] = "👤 Osoby"
            st.rerun()
    with col3:
        if st.button("🕸 Zobrazit vazby", use_container_width=True):
            st.session_state["current_screen"] = "🕸 Vazby"
            st.rerun()
    with col4:
        if st.button("🔗 Zobrazit graf", use_container_width=True):
            st.session_state["current_screen"] = "🔗 Graf vazeb"
            st.rerun()
    with col5:
        if st.button("⚠️ Zobrazit rizika", use_container_width=True):
            st.session_state["current_screen"] = "⚠️ Rizika"
            st.rerun()


def build_top_findings(results: list[dict[str, Any]]) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []

    high_risk_records = [record for record in results if record.get("risk_level") == "Vysoké"]
    if high_risk_records:
        names = ", ".join(record.get("nazev") or record.get("ico") for record in high_risk_records[:5])
        findings.append(
            {
                "title": f"Více signálů u {len(high_risk_records)} subjektů",
                "detail": f"Subjekty: {names}",
            }
        )

    liquidated_records = [record for record in results if record.get("v_likvidaci")]
    if liquidated_records:
        names = ", ".join(record.get("nazev") or record.get("ico") for record in liquidated_records[:5])
        findings.append(
            {
                "title": f"Likvidace u {len(liquidated_records)} subjektů",
                "detail": f"Subjekty: {names}",
            }
        )

    unreliable_vat = [record for record in results if record.get("nespolehlivy_platce") is True]
    if unreliable_vat:
        names = ", ".join(record.get("nazev") or record.get("ico") for record in unreliable_vat[:5])
        findings.append(
            {
                "title": f"DPH upozornění u {len(unreliable_vat)} subjektů",
                "detail": f"Subjekty: {names}",
            }
        )

    person_counts: dict[str, set[str]] = {}
    for record in results:
        for person in record.get("osoby", []) or []:
            person_name = person.get("jmeno")
            if person_name:
                person_counts.setdefault(person_name, set()).add(record.get("ico", ""))
    repeated_people = sorted(
        [(name, len(icos)) for name, icos in person_counts.items() if len(icos) > 1],
        key=lambda item: item[1],
        reverse=True,
    )
    if repeated_people:
        top_names = ", ".join(f"{name} ({count})" for name, count in repeated_people[:5])
        findings.append(
            {
                "title": f"Opakující se osoby: {len(repeated_people)}",
                "detail": top_names,
            }
        )

    address_counts: dict[str, set[str]] = {}
    for record in results:
        address = record.get("sidlo_raw") or record.get("sidlo")
        if address:
            address_counts.setdefault(address, set()).add(record.get("ico", ""))
    repeated_addresses = sorted(
        [(address, len(icos)) for address, icos in address_counts.items() if len(icos) > 1],
        key=lambda item: item[1],
        reverse=True,
    )
    if repeated_addresses:
        top_addresses = ", ".join(f"{address} ({count})" for address, count in repeated_addresses[:3])
        findings.append(
            {
                "title": f"Společné adresy: {len(repeated_addresses)}",
                "detail": top_addresses,
            }
        )

    return findings[:5]

def render_summary_tab(
    results: list[dict[str, Any]],
    relationship_scope: str,
    show_header: bool = True,
) -> bool:
    if show_header:
        st.subheader("Podrobnosti a zdroje")
    current_ico_block = "\n".join(rec.get("ico") for rec in results if rec.get("ico"))
    st.markdown("**Načtená IČA**")
    st.text_area(
        "IČA ke zkopírování",
        value=current_ico_block,
        height=min(220, 80 + 24 * max(len(results), 1)),
        key="current_ico_block",
    )

    compare_all_entities = st.checkbox(
        "Vybrat všechny osoby i navázané firmy a porovnat vše dohromady",
        key="compare_all_entities_global",
    )

    table_rows = []
    for record in results:
        table_rows.append(
            {
                "IČO": record.get("ico"),
                "Název": record.get("nazev"),
                "Sídlo": record.get("sidlo_raw") or record.get("sidlo"),
                "Stav": record.get("stav"),
                "V likvidaci": "Ano" if record.get("v_likvidaci") else "Ne",
                "Nespolehlivý plátce DPH": (
                    "Ano"
                    if record.get("nespolehlivy_platce") is True
                    else "Ne"
                    if record.get("nespolehlivy_platce") is False
                    else "Nelze ověřit"
                ),
                "Insolvence": record.get("probiha_insolvence"),
                "Rizikové signály": len(record.get("risk_flags", [])),
                "Úroveň rizika": record.get("risk_level"),
            }
        )
    df_results = pd.DataFrame(table_rows)

    def highlight_high_risk(row: pd.Series) -> list[str]:
        styles = [""] * len(row)
        if row["V likvidaci"] == "Ano" and row["Nespolehlivý plátce DPH"] == "Ano":
            styles = ["background-color: #ffcccc"] * len(row)
        elif row["Úroveň rizika"] == "Vysoké":
            styles = ["background-color: #ffe0b3"] * len(row)
        return styles

    st.dataframe(
        df_results.style.apply(highlight_high_risk, axis=1),
        use_container_width=True,
        height=min(400, 60 + 40 * len(df_results)),
    )
    st.caption("Zvýraznění pomáhá rychle najít firmy, které stojí za kontrolu.")
    st.caption(f"Režim vazeb: **{relationship_scope}**.")
    csv_data = df_results.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "⬇️ Stáhnout přehled jako CSV",
        data=csv_data,
        file_name=f"forenzni_analyza_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv",
    )
    return compare_all_entities


def render_risk_signals_screen(results: list[dict[str, Any]]) -> None:
    st.subheader("Rizikové signály")
    render_key_findings_intro(results)
    st.caption("Neutrální přehled údajů, které je vhodné ověřit ve zdroji.")
    with st.expander("Co to znamená?", expanded=True):
        render_meaning_section()
    with st.expander("Doporučené další kroky", expanded=True):
        render_next_steps_section()
    with st.expander("Vysvětlení pojmů", expanded=False):
        render_term_tooltips()

    total_flags = sum(len(record.get("risk_flags", []) or []) for record in results)
    if total_flags == 0:
        st.info("V aktuální analýze zatím nejsou automaticky nalezené rizikové signály.")
        return

    for record in results:
        flags = record.get("risk_flags", []) or []
        if not flags:
            continue

        st.markdown(f"### {record.get('nazev') or '(bez názvu)'}")
        st.caption(f"IČO: {record.get('ico')} · Úroveň: {record.get('risk_level') or 'Nutno ověřit'}")

        for flag in flags:
            with st.container(border=True):
                info_col, source_col = st.columns([3, 1])
                with info_col:
                    st.markdown(f"**{flag.get('signal') or 'Rizikový signál'}**")
                    st.write(
                        f"Subjekt: {record.get('nazev') or '(bez názvu)'} ({record.get('ico')})"
                    )
                    st.caption(
                        f"Popis: {flag.get('signal') or 'Byl zachycen signál k ověření.'}"
                    )
                with source_col:
                    st.metric("Závažnost", record.get("risk_level") or "Nutno ověřit")

                if flag.get("jistota"):
                    st.caption(f"Jistota: {flag.get('jistota')}")
                if flag.get("zdroj"):
                    st.markdown(f"[Zdroj pro ověření]({flag.get('zdroj')})")
                else:
                    st.caption("Zdroj: nutno ověřit ručně.")
