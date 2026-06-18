"""Detail jednotlivých firem."""

from typing import Any

import pandas as pd
import streamlit as st

from core.config import JUSTICE_VYPIS_URL
from core.utils import format_kurzy_search_link


def render_companies_screen(
    results: list[dict[str, Any]],
    include_historical: bool,
) -> None:
    st.subheader("Firmy")
    st.caption("Přehled načtených subjektů a jejich základních vazeb.")

    company_rows = []
    for record in results:
        people_count = len(record.get("osoby", []) or [])
        linked_count = len(record.get("navazane_firmy", []) or [])
        company_rows.append(
            {
                "IČO": record.get("ico"),
                "Název": record.get("nazev"),
                "Stav": (
                    "Nenalezeno v ARES – ověřit ručně"
                    if record.get("ares_status") == "nenalezeno_v_ares"
                    else record.get("stav")
                ),
                "Sídlo": record.get("sidlo_raw") or record.get("sidlo"),
                "Počet osob": people_count,
                "Počet vazeb": people_count + linked_count,
                "Rizika": len(record.get("risk_flags", []) or []),
            }
        )
    st.dataframe(pd.DataFrame(company_rows), use_container_width=True)
    render_company_detail_section(results, include_historical)


def render_people_screen(
    results: list[dict[str, Any]],
    include_historical: bool,
) -> tuple[list[dict[str, Any]], bool]:
    st.subheader("Osoby")
    st.caption("Osoby nalezené napříč firmami. Opakující se osoby jsou zvýrazněné.")

    selected_people = render_people_selection(results, include_historical)
    run_selected_people_relationships = st.button(
        "Použít vybrané osoby pro analýzu vazeb",
        type="primary",
        use_container_width=True,
    )
    return selected_people, run_selected_people_relationships


def render_people_selection(
    results: list[dict[str, Any]],
    include_historical: bool,
) -> list[dict[str, Any]]:
    people_rows = []
    person_company_counts: dict[str, set[str]] = {}

    for record in results:
        for person in record.get("osoby", []) or []:
            person_name = person.get("jmeno")
            if person_name:
                person_company_counts.setdefault(person_name, set()).add(record.get("ico", ""))
            people_rows.append(
                {
                    "Osoba": person.get("jmeno"),
                    "Role": person.get("role"),
                    "Firma": record.get("nazev"),
                    "IČO": record.get("ico"),
                    "Počet firem": len(person_company_counts.get(person.get("jmeno"), set())),
                    "Vazba": person.get("stav_vazby"),
                    "Od": person.get("od"),
                    "Do": person.get("do"),
                }
            )

    if not people_rows:
        st.info("V aktuálním případu zatím nejsou dohledané žádné osoby.")
        return []

    df_people = pd.DataFrame(people_rows)
    df_people["Počet firem"] = df_people["Osoba"].map(
        lambda name: len(person_company_counts.get(name, set()))
    )
    repeat_only = st.checkbox("Jen opakující se osoby", key="people_repeat_only")
    if repeat_only:
        df_people = df_people[df_people["Počet firem"] > 1]

    def highlight_repeated(row: pd.Series) -> list[str]:
        if row["Počet firem"] > 1:
            return ["background-color: #fff3cd"] * len(row)
        return [""] * len(row)

    st.dataframe(
        df_people.style.apply(highlight_repeated, axis=1),
        use_container_width=True,
    )

    st.markdown("### Výběr osob")
    selected_people: list[dict[str, Any]] = []
    people_cols = st.columns(2)
    deduped_rows = df_people.drop_duplicates(subset=["Osoba", "Firma", "Role", "Od", "Do"])
    for index, row in deduped_rows.iterrows():
        person_key = f"{row['IČO']}|{row['Osoba']}|{row['Role']}|{row['Od']}|{row['Do']}"
        label = f"{row['Osoba']} | {row['Role']} | {row['Firma']}"
        with people_cols[index % 2]:
            checked = st.checkbox(label, key=f"select_person_{person_key}")
        if checked:
            selected_people.append(
                {
                    "person_key": person_key,
                    "jmeno": row["Osoba"],
                    "role": row["Role"],
                    "firma": row["Firma"],
                    "ico": row["IČO"],
                    "stav_vazby": row["Vazba"],
                    "kurzy_vazby_link": format_kurzy_search_link(
                        str(row["Osoba"]),
                        not include_historical,
                    ),
                }
            )
    return selected_people


def render_company_detail_section(
    results: list[dict[str, Any]],
    include_historical: bool,
) -> list[dict[str, Any]]:
    selected_people: list[dict[str, Any]] = []

    st.markdown("### Detail firem")
    for record in results:
        with st.expander(f"{record.get('nazev') or '(neznámý název)'} — IČO {record.get('ico')}"):
            c1, c2 = st.columns(2)

            with c1:
                st.markdown("**Základní údaje (ARES)**")
                st.write(f"Sídlo: {record.get('sidlo_raw') or record.get('sidlo') or '—'}")
                st.write(f"Právní forma: {record.get('pravni_forma') or '—'}")
                st.write(f"Datum vzniku: {record.get('datum_vzniku') or '—'}")
                st.write(f"Datum zániku: {record.get('datum_zaniku') or '—'}")
                if record.get("ares_status") != "ok":
                    st.warning(f"ARES: {record.get('ares_chyba') or record.get('ares_status')}")
                st.markdown(f"[🔗 Zdroj – ARES]({record.get('zdroj_ares')})")

            with c2:
                st.markdown("**Rizikové signály**")
                flags = record.get("risk_flags", [])
                if not flags:
                    st.write("Žádné automaticky zjištěné rizikové signály.")
                for flag in flags:
                    st.markdown(f"- **{flag['signal']}**")
                    st.caption(
                        f"Jistota: {flag['jistota']} · [zdroj]({flag['zdroj']})"
                        if flag["zdroj"]
                        else f"Jistota: {flag['jistota']}"
                    )

            st.markdown("---")
            st.markdown("**Osoby spojené s firmou**")
            osoby = record.get("osoby", [])
            if osoby:
                st.dataframe(pd.DataFrame(osoby), use_container_width=True)
                helper_col, toggle_col = st.columns([4, 1])
                with helper_col:
                    st.caption("Zaklikni osoby, které chceš použít pro hledání vazeb.")
                with toggle_col:
                    select_all_people = st.checkbox(
                        "Vybrat všechny",
                        key=f"select_all_people_{record.get('ico')}",
                    )
                person_cols = st.columns(2)
                for person_index, osoba in enumerate(osoby):
                    person_key = (
                        f"{record.get('ico')}|{osoba.get('jmeno')}|"
                        f"{osoba.get('role')}|{osoba.get('od')}|{osoba.get('do')}"
                    )
                    checkbox_key = f"select_person_{person_key}"
                    if select_all_people:
                        st.session_state[checkbox_key] = True
                    label = f"{osoba.get('jmeno')} | {osoba.get('role')} | {osoba.get('stav_vazby')}"
                    with person_cols[person_index % 2]:
                        checked = st.checkbox(label, key=checkbox_key)
                    if checked:
                        selected_people.append(
                            {
                                "person_key": person_key,
                                "jmeno": osoba.get("jmeno"),
                                "role": osoba.get("role"),
                                "firma": record.get("nazev") or "(neznámý název)",
                                "ico": record.get("ico"),
                                "stav_vazby": osoba.get("stav_vazby"),
                                "kurzy_vazby_link": osoba.get("kurzy_vazby_link"),
                            }
                        )
            else:
                vr_status = record.get("vr_status")
                if vr_status == "ok":
                    st.write("Žádné osoby nebyly v rejstříku dohledány.")
                else:
                    st.info(
                        f"Osoby nelze automaticky dohledat ({record.get('vr_chyba') or vr_status}). "
                        f"Zkontroluj ručně: [Veřejný rejstřík]({JUSTICE_VYPIS_URL.format(ico=record.get('ico'))})"
                    )

            st.markdown("---")
            st.markdown("**Navázané firmy dohledané přes ARES VR**")
            navazane_firmy = record.get("navazane_firmy", [])
            if navazane_firmy:
                st.dataframe(pd.DataFrame(navazane_firmy), use_container_width=True)
            else:
                st.write("Žádné další navázané právnické osoby se nepodařilo automaticky vyčíst.")

            st.markdown("---")
            st.markdown("**Další dohledání vazeb přes Kurzy.cz**")
            st.markdown(
                f"- 🔎 Firma v Kurzy.cz: "
                f"[vyhledat {record.get('ico')}]({format_kurzy_search_link(record.get('ico'), not include_historical)})"
            )
            if osoby:
                for osoba in osoby[:12]:
                    st.markdown(
                        f"- 👤 {osoba['jmeno']}: "
                        f"[vyhledat vazby]({osoba['kurzy_vazby_link']})"
                    )

            st.markdown("---")
            st.markdown("**Externí ověření (doporučeno zkontrolovat ručně)**")
            st.markdown(
                f"- 📄 Sbírka listin: [{record.get('link_sbirka_listin')}]({record.get('link_sbirka_listin')})"
            )
            st.markdown(
                f"- ⚖️ Insolvenční rejstřík: [{record.get('link_isir')}]({record.get('link_isir')})"
            )
            if record.get("ares_status") == "nenalezeno_v_ares":
                st.markdown(
                    f"- 🔎 Justice.cz fallback: "
                    f"[{record.get('fallback_lookup_justice')}]({record.get('fallback_lookup_justice')})"
                )
                st.markdown(
                    f"- 🔎 Kurzy.cz fallback: "
                    f"[{record.get('fallback_lookup_kurzy')}]({record.get('fallback_lookup_kurzy')})"
                )
                st.caption(record.get("fallback_lookup_note"))
            if record.get("isir_chyba"):
                st.caption(f"Poznámka ISIR: {record.get('isir_chyba')}")
            if record.get("sbirka_chyba"):
                st.caption(f"Poznámka sbírka listin: {record.get('sbirka_chyba')}")

    return selected_people
