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
        "run_analysis": False,
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
                    actions["run_analysis"],
                ) = render_input_controls()
    else:
        render_landing_sections()
        with st.container(border=True):
            st.markdown("### 🔎 Nová analýza")
            st.caption("Vložte jedno nebo více IČO. Každé IČO může být na samostatném řádku.")
            render_new_case_action("overview_empty")
            (
                actions["input_text"],
                actions["include_historical"],
                actions["expansion_depth"],
                actions["auto_include_all_entities_initial"],
                actions["run_analysis"],
            ) = render_input_controls()
        with st.expander("Co to znamená?", expanded=True):
            render_meaning_section()
        with st.expander("Doporučené další kroky", expanded=True):
            render_next_steps_section()
        with st.expander("Vysvětlení pojmů", expanded=False):
            render_term_tooltips()

    return actions


def render_landing_sections() -> None:
    st.markdown(
        """
        <style>
        .connexa-home {
            padding: 1.1rem 0 0.7rem 0;
        }
        .connexa-hero-layout {
            display:grid;
            grid-template-columns: minmax(280px, 0.92fr) minmax(360px, 1.08fr);
            gap: clamp(1.5rem, 5vw, 4rem);
            align-items:center;
        }
        .connexa-eyebrow {
            color:#3158F6;
            font-weight:800;
            font-size:0.88rem;
            margin-bottom:0.8rem;
            letter-spacing:0;
        }
        .connexa-title {
            margin:0;
            max-width:720px;
            color:#06143A;
            font-size:clamp(2.55rem, 5.2vw, 5.25rem);
            line-height:1.06;
            font-weight:850;
            letter-spacing:0;
        }
        .connexa-title span {color:#3158F6;}
        .connexa-lead {
            max-width:650px;
            color:#475777;
            font-size:clamp(1.05rem, 1.6vw, 1.28rem);
            line-height:1.55;
            margin:1.35rem 0 1.55rem 0;
        }
        .connexa-hero-hint {
            color:#5D6B8A;
            font-size:0.9rem;
            margin:0.35rem 0 0 0.1rem;
        }
        .connexa-stat-row {
            display:flex;
            flex-wrap:wrap;
            gap:1rem;
            margin-top:2.1rem;
        }
        .connexa-stat {
            display:flex;
            align-items:center;
            gap:0.85rem;
            min-width:132px;
            padding-right:1.4rem;
            border-right:1px solid #E2E8F0;
        }
        .connexa-stat:last-child {border-right:0;}
        .connexa-stat-icon {
            width:46px;
            height:46px;
            display:grid;
            place-items:center;
            border-radius:16px;
            background:#EEF3FF;
            color:#3158F6;
            font-size:1.4rem;
        }
        .connexa-stat strong {
            display:block;
            color:#06143A;
            font-size:1.02rem;
            line-height:1.15;
        }
        .connexa-stat span {
            display:block;
            color:#52617F;
            font-size:0.88rem;
            margin-top:0.15rem;
        }
        .connexa-map {
            position:relative;
            min-height:510px;
            border-radius:32px;
            background:
                radial-gradient(circle at 52% 48%, rgba(49,88,246,.12), transparent 0 165px),
                radial-gradient(circle at 50% 50%, transparent 0 120px, rgba(49,88,246,.09) 121px 122px, transparent 123px 205px, rgba(49,88,246,.055) 206px 207px, transparent 208px),
                linear-gradient(180deg, #FFFFFF, #F8FBFF);
            overflow:hidden;
        }
        .connexa-map:before {
            content:"";
            position:absolute;
            inset:54px 48px;
            background:
                linear-gradient(90deg, transparent 0 49.8%, rgba(49,88,246,.26) 50%, transparent 50.2%),
                linear-gradient(0deg, transparent 0 49.8%, rgba(49,88,246,.20) 50%, transparent 50.2%);
            transform:rotate(12deg);
            opacity:.65;
        }
        .connexa-center-node {
            position:absolute;
            left:50%;
            top:50%;
            transform:translate(-50%,-50%);
            width:190px;
            height:190px;
            border-radius:999px;
            border:2px solid #3158F6;
            background:#fff;
            box-shadow:0 22px 60px rgba(49,88,246,.18);
            display:flex;
            flex-direction:column;
            align-items:center;
            justify-content:center;
            text-align:center;
            color:#06143A;
        }
        .connexa-center-node .building {font-size:2.6rem; margin-bottom:0.35rem;}
        .connexa-center-node strong {font-size:0.98rem;}
        .connexa-center-node span {font-size:0.86rem; margin-top:0.3rem;}
        .connexa-node {
            position:absolute;
            display:flex;
            align-items:center;
            gap:0.7rem;
            min-width:178px;
            padding:0.75rem 0.9rem;
            border:1px solid #E7ECF7;
            border-radius:999px;
            background:rgba(255,255,255,.92);
            box-shadow:0 16px 42px rgba(15,23,42,.08);
            color:#06143A;
        }
        .connexa-node .bubble {
            width:42px;
            height:42px;
            border-radius:999px;
            display:grid;
            place-items:center;
            flex:0 0 auto;
            font-size:1.35rem;
        }
        .connexa-node strong {display:block; font-size:0.84rem; line-height:1.12;}
        .connexa-node span {display:block; font-size:0.72rem; color:#52617F; margin-top:0.15rem;}
        .node-company .bubble {background:#F0EEFF; color:#6C4DFF;}
        .node-person .bubble {background:#DCFCE7; color:#16A34A;}
        .node-address .bubble {background:#FFF3D7; color:#F59E0B;}
        .node-risk .bubble {background:#FEE2E2; color:#DC2626;}
        .n1 {left:7%; top:18%;}
        .n2 {right:5%; top:20%;}
        .n3 {right:8%; top:52%;}
        .n4 {left:2%; top:49%;}
        .n5 {left:13%; bottom:12%;}
        .n6 {right:24%; bottom:5%;}
        .n7 {left:44%; top:4%;}
        .connexa-dot {
            position:absolute;
            width:9px;
            height:9px;
            border-radius:999px;
            background:#3158F6;
            box-shadow:0 0 0 7px rgba(49,88,246,.10);
        }
        .d1 {left:33%; top:37%;}
        .d2 {right:29%; top:31%;}
        .d3 {left:48%; bottom:22%; background:#8B5CF6;}
        .d4 {right:17%; bottom:30%; background:#E85AAD;}
        .connexa-source-title {
            text-align:center;
            color:#657391;
            margin:1.8rem 0 1rem;
            font-size:0.96rem;
        }
        .connexa-sources {
            display:grid;
            grid-template-columns: repeat(6, minmax(100px, 1fr));
            gap:1rem;
            align-items:start;
            color:#8A96AE;
            margin-bottom:1.6rem;
        }
        .connexa-source {
            text-align:center;
            font-weight:800;
            font-size:1rem;
        }
        .connexa-source span {
            display:block;
            font-weight:500;
            font-size:0.72rem;
            margin-top:0.25rem;
            line-height:1.3;
        }
        .connexa-trust {
            display:flex;
            justify-content:space-between;
            align-items:center;
            gap:1rem;
            max-width:1040px;
            margin:1rem auto 0.5rem;
            padding:1.15rem 1.35rem;
            border:1px solid #E2E8F0;
            border-radius:14px;
            background:#fff;
            box-shadow:0 18px 42px rgba(15,23,42,.045);
        }
        .connexa-trust-main {
            display:flex;
            align-items:center;
            gap:1rem;
            color:#06143A;
        }
        .connexa-trust-icon {
            width:48px;
            height:48px;
            border-radius:14px;
            display:grid;
            place-items:center;
            background:#EEF3FF;
            color:#3158F6;
            font-size:1.45rem;
        }
        .connexa-trust strong {display:block; font-size:1.15rem;}
        .connexa-trust span {display:block; color:#52617F; font-size:0.92rem; margin-top:0.15rem;}
        .connexa-trust-cta {
            color:#3158F6;
            border:1px solid #3158F6;
            border-radius:8px;
            padding:0.72rem 1rem;
            font-weight:800;
            white-space:nowrap;
        }
        @media (max-width: 1100px) {
            .connexa-hero-layout {grid-template-columns:1fr;}
            .connexa-map {min-height:470px;}
        }
        @media (max-width: 760px) {
            .connexa-home {padding-top:0.35rem;}
            .connexa-title {font-size:2.55rem;}
            .connexa-map {min-height:620px; border-radius:22px;}
            .connexa-node {left:50% !important; right:auto !important; min-width:230px; transform:translateX(-50%);}
            .n1 {top:8%;}
            .n7 {top:19%;}
            .n2 {top:30%;}
            .n4 {top:66%;}
            .n3 {top:77%;}
            .n5 {bottom:4%;}
            .n6 {display:none;}
            .connexa-center-node {width:155px; height:155px;}
            .connexa-sources {grid-template-columns:repeat(2, minmax(120px, 1fr));}
            .connexa-trust {align-items:flex-start; flex-direction:column;}
            .connexa-trust-cta {width:100%; text-align:center;}
            .connexa-stat {border-right:0;}
        }
        </style>
        <section class="connexa-home">
          <div class="connexa-hero-layout">
            <div>
              <div class="connexa-eyebrow">Analýza firemních vazeb a propojení</div>
              <h1 class="connexa-title">Odhalujeme souvislosti skryté ve <span>firemních vazbách.</span></h1>
              <p class="connexa-lead">
                Propojujeme firmy, osoby a adresy do přehledné mapy vztahů,
                abyste mohli dělat informovanější rozhodnutí.
              </p>
              <p class="connexa-hero-hint">Zadejte IČO níže a spusťte analýzu veřejných zdrojů.</p>
              <div class="connexa-stat-row">
                <div class="connexa-stat"><div class="connexa-stat-icon">🏢</div><div><strong>Firmy</strong><span>z veřejných registrů</span></div></div>
                <div class="connexa-stat"><div class="connexa-stat-icon">🔗</div><div><strong>Vazby</strong><span>osoby, firmy, adresy</span></div></div>
                <div class="connexa-stat"><div class="connexa-stat-icon">⚠️</div><div><strong>Signály</strong><span>nutno ověřit</span></div></div>
                <div class="connexa-stat"><div class="connexa-stat-icon">↩</div><div><strong>Historie</strong><span>aktuální i historické</span></div></div>
              </div>
            </div>
            <div class="connexa-map" aria-label="Ilustrační mapa firemních vazeb">
              <div class="connexa-dot d1"></div>
              <div class="connexa-dot d2"></div>
              <div class="connexa-dot d3"></div>
              <div class="connexa-dot d4"></div>
              <div class="connexa-center-node"><div class="building">🏢</div><strong>DEMO COMPANY s.r.o.</strong><span>IČO: zadaný subjekt</span></div>
              <div class="connexa-node node-company n1"><div class="bubble">🏢</div><div><strong>COMPANY A s.r.o.</strong><span>Společná firma</span></div></div>
              <div class="connexa-node node-company n2"><div class="bubble">🏢</div><div><strong>COMPANY B a.s.</strong><span>Propojená firma</span></div></div>
              <div class="connexa-node node-person n3"><div class="bubble">👤</div><div><strong>Petr Svoboda</strong><span>Společník</span></div></div>
              <div class="connexa-node node-address n4"><div class="bubble">📍</div><div><strong>Na Příkopě 123/4</strong><span>Společná adresa</span></div></div>
              <div class="connexa-node node-person n5"><div class="bubble">👤</div><div><strong>Jiří Veselý</strong><span>Jednatel</span></div></div>
              <div class="connexa-node node-company n6"><div class="bubble">🏢</div><div><strong>COMPANY C s.r.o.</strong><span>Navázaná firma</span></div></div>
              <div class="connexa-node node-risk n7"><div class="bubble">⚠️</div><div><strong>Rizikový signál</strong><span>Nutno ověřit</span></div></div>
            </div>
          </div>

          <div class="connexa-source-title">Pracujeme s veřejnými zdroji dat</div>
          <div class="connexa-sources">
            <div class="connexa-source">ARES<span>Administrativní registr ekonomických subjektů</span></div>
            <div class="connexa-source">OR<span>Obchodní rejstřík</span></div>
            <div class="connexa-source">RŽP<span>Registr živnostenského podnikání</span></div>
            <div class="connexa-source">ADIS<span>Registr DPH</span></div>
            <div class="connexa-source">Justice.cz<span>Veřejný rejstřík a ISIR</span></div>
            <div class="connexa-source">a další<span>veřejné zdroje</span></div>
          </div>

          <div class="connexa-trust">
            <div class="connexa-trust-main">
              <div class="connexa-trust-icon">🛡</div>
              <div><strong>Důvěřujte, ale prověřujte.</strong><span>Connexa ukáže vazby a zdroje. Závěry vždy ověřujte v původním registru.</span></div>
            </div>
            <div class="connexa-trust-cta">Zjistit více o funkcích →</div>
          </div>
        </section>
        """,
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
