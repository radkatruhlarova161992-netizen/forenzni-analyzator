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
                    actions["refresh_data"],
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
                actions["refresh_data"],
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
            padding: 0.4rem 0 0.8rem 0;
            max-width: 880px;
        }
        .connexa-title {
            margin:0;
            color:#06143A;
            font-size:clamp(2.15rem, 4.8vw, 4.15rem);
            line-height:1.08;
            font-weight:800;
            letter-spacing:0;
        }
        .connexa-lead {
            color:#475777;
            font-size:clamp(1rem, 1.45vw, 1.16rem);
            line-height:1.55;
            margin:1rem 0 1.25rem 0;
        }
        .connexa-capabilities-title {
            color:#06143A;
            font-size:1rem;
            font-weight:700;
            margin:1.25rem 0 0.55rem 0;
        }
        .connexa-capabilities {
            display:flex;
            flex-wrap:wrap;
            gap:0.65rem;
        }
        .connexa-capability {
            padding:0.55rem 0.85rem;
            border:1px solid #E2E8F0;
            border-radius:999px;
            background:#F8FAFC;
            color:#334155;
            font-size:0.92rem;
            font-weight:600;
            line-height:1.2;
        }
        @media (max-width: 760px) {
            .connexa-title {font-size:2.2rem;}
            .connexa-capabilities {gap:0.5rem;}
        }
        </style>
        <section class="connexa-home">
          <h1 class="connexa-title">Odhalujeme příběhy skryté ve firemních vazbách.</h1>
          <p class="connexa-lead">
            Propojujeme firmy, osoby a adresy do přehledné mapy vztahů,
            abyste mohli dělat informovanější rozhodnutí.
          </p>
          <div class="connexa-capabilities-title">Co Connexa umí:</div>
          <div class="connexa-capabilities">
            <div class="connexa-capability">firmy</div>
            <div class="connexa-capability">osoby</div>
            <div class="connexa-capability">adresy</div>
            <div class="connexa-capability">vazby</div>
            <div class="connexa-capability">rizikové signály</div>
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
