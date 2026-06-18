"""UI pro vztahy a porovnání bez fetchování a bez analýzy."""

from itertools import combinations
from typing import Any

import pandas as pd
import streamlit as st

from core.utils import format_kurzy_search_link
from ui.explainers import (
    render_key_findings_intro,
    render_meaning_section,
    render_next_steps_section,
    render_term_tooltips,
    tooltip_term,
)

NO_DIRECT_INTERSECTION_TEXT = "Nebyl nalezen přímý průnik v načtených datech."


def render_relationships_screen(
    results: list[dict[str, Any]],
    relationship_graph: dict[str, pd.DataFrame],
    selected_people_names: list[str],
    selected_people_rows: list[dict[str, Any]],
    intersections: dict[str, Any],
    relationship_include_all_entities: bool,
    include_historical: bool,
) -> tuple[str, bool, bool]:
    st.subheader("Vazby")
    render_key_findings_intro(results)
    st.caption("Tady rychle uvidíš, proč spolu firmy souvisejí.")
    show_external_relationships = st.checkbox(
        "Zahrnout rozšířené externí vazby",
        value=st.session_state.get("relationships_show_external", True),
        key="relationships_show_external",
        help="Zobrazí i vazby z veřejných agregátorů. Tyto vazby jsou označené jako nutno ověřit.",
    )
    with st.expander("Co to znamená?", expanded=True):
        render_meaning_section()
    with st.expander("Doporučené další kroky", expanded=True):
        render_next_steps_section()
    with st.expander("Vysvětlení pojmů", expanded=False):
        render_term_tooltips()

    shared_people = build_shared_people_view(relationship_graph["person_occurrences"])
    shared_addresses = build_shared_addresses_view(results)
    company_links = filter_external_rows(
        relationship_graph["company_links"],
        show_external_relationships,
    )
    participant_edges = filter_external_rows(
        relationship_graph["participant_edges"],
        show_external_relationships,
    )
    historical_relationships = build_historical_relationships_view(
        participant_edges
    )
    legal_entity_links = build_legal_entity_link_view(company_links)
    text_map = build_text_relationship_map(results, show_external_relationships)

    summary_col1, summary_col2, summary_col3, summary_col4 = st.columns(4)
    with summary_col1:
        st.metric("Společné osoby", len(shared_people))
    with summary_col2:
        st.metric("Společné adresy", len(shared_addresses))
    with summary_col3:
        st.metric("Propojené firmy", len(legal_entity_links))
    with summary_col4:
        st.metric("Historické vazby", len(historical_relationships))

    render_relationship_section(
        f"Společné osoby ({tooltip_term('jednatel')}, {tooltip_term('společník')})",
        shared_people,
        NO_DIRECT_INTERSECTION_TEXT,
        use_html=True,
    )
    render_relationship_section(
        "Společné adresy",
        shared_addresses,
        NO_DIRECT_INTERSECTION_TEXT,
    )
    render_relationship_section(
        "Propojení přes právnické osoby",
        legal_entity_links,
        NO_DIRECT_INTERSECTION_TEXT,
    )
    render_relationship_section(
        tooltip_term("historická vazba"),
        historical_relationships,
        NO_DIRECT_INTERSECTION_TEXT,
        use_html=True,
    )
    render_source_diagnostics(results)

    st.markdown("### Textová mapa vazeb")
    if not text_map.strip():
        st.info("Textovou mapu se nepodařilo sestavit z načtených dat.")
    else:
        st.code(text_map, language="text")

    st.markdown("### Nejvýznamnější uzly")
    key_nodes = build_key_nodes(
        shared_people,
        shared_addresses,
        participant_edges,
    )
    people_col, address_col, company_col = st.columns(3)
    with people_col:
        st.markdown("**Osoby s nejvíce vazbami**")
        render_small_table(key_nodes["people"], NO_DIRECT_INTERSECTION_TEXT)
    with address_col:
        st.markdown("**Adresy s nejvíce vazbami**")
        render_small_table(key_nodes["addresses"], NO_DIRECT_INTERSECTION_TEXT)
    with company_col:
        st.markdown("**Firmy s nejvíce vazbami**")
        render_small_table(key_nodes["companies"], NO_DIRECT_INTERSECTION_TEXT)

    with st.expander("Vybrané osoby a jejich výskyty", expanded=False):
        render_selected_people_results(
            selected_people_names,
            selected_people_rows,
            intersections,
            relationship_include_all_entities,
            include_historical,
        )

    with st.expander("Rozšířit síť vazeb", expanded=False):
        extra_ico_text, auto_include_all_entities_extra, add_relationship_companies = (
            render_relationships_controls()
        )

    return (
        extra_ico_text,
        auto_include_all_entities_extra,
        add_relationship_companies,
    )


def render_intersections_screen(
    cross_analysis_payload: dict[str, Any] | None,
) -> tuple[bool, str, str]:
    st.subheader("Průniky")
    st.caption("Rozšířené porovnání společných osob, adres a rolí mezi subjekty v případu.")
    run_cross_analysis, cross_people_text, cross_ico_text = render_cross_analysis_inputs()
    if cross_analysis_payload:
        render_cross_analysis_results(
            cross_analysis_payload["cross_analysis"],
            cross_analysis_payload["cross_analysis_summary"],
        )
    else:
        st.info("Zadej osoby nebo další IČA a spusť rozšířené porovnání.")

    return run_cross_analysis, cross_people_text, cross_ico_text


def build_shared_people_view(person_occurrences: pd.DataFrame) -> pd.DataFrame:
    if person_occurrences.empty:
        return pd.DataFrame(
            columns=[
                "Jméno osoby",
                "Počet firem",
                "Seznam firem",
                "Role osoby",
                "Aktuální / historická vazba",
            ]
        )

    rows: list[dict[str, Any]] = []
    grouped = person_occurrences.groupby("Osoba")
    for person_name, group in grouped:
        firm_count = group["IČO"].nunique()
        if firm_count <= 1:
            continue

        roles = sorted({str(value).strip() for value in group["Role"] if value})
        statuses = sorted(
            {
                classify_relationship_state(
                    stav_vazby=row.get("Stav vazby"),
                    date_to=row.get("Do"),
                )
                for _, row in group.iterrows()
            }
        )
        rows.append(
            {
                "Jméno osoby": person_name,
                "Počet firem": firm_count,
                "Seznam firem": ", ".join(sorted(set(group["Firma"]))),
                "Role osoby": ", ".join(roles) if roles else "neuvedeno",
                "Aktuální / historická vazba": summarize_relationship_states(statuses),
            }
        )

    if not rows:
        return pd.DataFrame(
            columns=[
                "Jméno osoby",
                "Počet firem",
                "Seznam firem",
                "Role osoby",
                "Aktuální / historická vazba",
            ]
        )

    return pd.DataFrame(rows).sort_values(
        ["Počet firem", "Jméno osoby"], ascending=[False, True]
    )


def build_shared_addresses_view(results: list[dict[str, Any]]) -> pd.DataFrame:
    address_rows: list[dict[str, str]] = []
    for record in results:
        address = record.get("sidlo_raw") or record.get("sidlo")
        if not address:
            continue
        address_rows.append(
            {
                "Adresa": address,
                "Firma": record.get("nazev") or "(neznámý název)",
                "IČO": record.get("ico") or "",
            }
        )

        for relation in record.get("navazane_firmy", []) or []:
            relation_address = relation.get("adresa")
            if not relation_address:
                continue
            if relation.get("entity_type") != "address" and relation.get("typ_vazby") != "společná adresa":
                continue
            address_rows.append(
                {
                    "Adresa": relation_address,
                    "Firma": record.get("nazev") or "(neznámý název)",
                    "IČO": record.get("ico") or "",
                }
            )

    if not address_rows:
        return pd.DataFrame(columns=["Adresa", "Počet firem", "Seznam firem"])

    address_df = pd.DataFrame(address_rows)
    shared = (
        address_df.groupby("Adresa")
        .agg(
            **{
                "Počet firem": ("IČO", "nunique"),
                "Seznam firem": ("Firma", lambda x: ", ".join(sorted(set(x)))),
            }
        )
        .reset_index()
    )
    shared = shared[shared["Počet firem"] > 1]
    if shared.empty:
        return pd.DataFrame(columns=["Adresa", "Počet firem", "Seznam firem"])
    return shared.sort_values(["Počet firem", "Adresa"], ascending=[False, True])


def filter_external_rows(dataframe: pd.DataFrame, show_external: bool) -> pd.DataFrame:
    if show_external or dataframe.empty or "Ověření" not in dataframe.columns:
        return dataframe
    return dataframe[dataframe["Ověření"] != "nutno ověřit"]


def build_historical_relationships_view(participant_edges: pd.DataFrame) -> pd.DataFrame:
    if participant_edges.empty:
        return pd.DataFrame(columns=["Osoba", "Firma", "Role", "Od", "Do"])

    rows: list[dict[str, Any]] = []
    for _, row in participant_edges.iterrows():
        if row.get("Typ účastníka") != "Osoba":
            continue
        state = classify_relationship_state(
            stav_vazby=row.get("Stav vazby"),
            date_to=row.get("Do"),
        )
        if state != "Historická":
            continue
        rows.append(
            {
                "Osoba": row.get("Účastník"),
                "Firma": row.get("Firma"),
                "Role": row.get("Role") or "neuvedeno",
                "Od": row.get("Od") or "neuvedeno",
                "Do": row.get("Do") or "neuvedeno",
            }
        )

    if not rows:
        return pd.DataFrame(columns=["Osoba", "Firma", "Role", "Od", "Do"])

    return (
        pd.DataFrame(rows)
        .drop_duplicates()
        .sort_values(["Osoba", "Firma", "Od"], ascending=[True, True, True])
        .reset_index(drop=True)
    )


def build_legal_entity_link_view(company_links: pd.DataFrame) -> pd.DataFrame:
    if company_links.empty:
        return pd.DataFrame(
            columns=[
                "Zdrojová firma",
                "Propojující firma",
                "Cílová firma",
                "Typ vazby",
                "Zdroj",
                "Důvěryhodnost",
                "Ověření",
                "Odkaz",
            ]
        )

    grouped: dict[str, list[dict[str, Any]]] = {}
    for _, row in company_links.iterrows():
        connector_name = row.get("Navázaná firma")
        connector_ico = row.get("Navázané IČO")
        if not connector_name:
            continue
        connector_key = f"{connector_name}|{connector_ico or ''}"
        grouped.setdefault(connector_key, []).append(row.to_dict())

    rows: list[dict[str, str]] = []
    for connector_key, link_rows in grouped.items():
        if len(link_rows) < 2:
            continue
        connector_name = link_rows[0].get("Navázaná firma") or "(neznámá firma)"
        connector_label = connector_name
        if link_rows[0].get("Navázané IČO"):
            connector_label = f"{connector_name} ({link_rows[0].get('Navázané IČO')})"

        for left, right in combinations(link_rows, 2):
            left_company = left.get("Výchozí firma") or "(neznámý název)"
            right_company = right.get("Výchozí firma") or "(neznámý název)"
            if left_company == right_company:
                continue
            type_parts = sorted(
                {
                    value
                    for value in [
                        left.get("Role"),
                        left.get("Stav vazby"),
                        right.get("Role"),
                        right.get("Stav vazby"),
                    ]
                    if value
                }
            )
            rows.append(
                {
                    "Zdrojová firma": left_company,
                    "Propojující firma": connector_label,
                    "Cílová firma": right_company,
                    "Typ vazby": ", ".join(type_parts) if type_parts else "nutno ověřit",
                    "Zdroj": ", ".join(
                        sorted(
                            {
                                str(value)
                                for value in [left.get("Zdroj"), right.get("Zdroj")]
                                if value
                            }
                        )
                    )
                    or "neuvedeno",
                    "Důvěryhodnost": ", ".join(
                        sorted(
                            {
                                str(value)
                                for value in [
                                    left.get("Důvěryhodnost"),
                                    right.get("Důvěryhodnost"),
                                ]
                                if value
                            }
                        )
                    )
                    or "neuvedeno",
                    "Ověření": ", ".join(
                        sorted(
                            {
                                str(value)
                                for value in [left.get("Ověření"), right.get("Ověření")]
                                if value
                            }
                        )
                    )
                    or "nutno ověřit",
                    "Odkaz": left.get("Odkaz") or right.get("Odkaz") or "",
                }
            )

    if not rows:
        return pd.DataFrame(
            columns=[
                "Zdrojová firma",
                "Propojující firma",
                "Cílová firma",
                "Typ vazby",
                "Zdroj",
                "Důvěryhodnost",
                "Ověření",
                "Odkaz",
            ]
        )

    return (
        pd.DataFrame(rows)
        .drop_duplicates()
        .sort_values(
            ["Zdrojová firma", "Propojující firma", "Cílová firma"],
            ascending=[True, True, True],
        )
        .reset_index(drop=True)
    )


def build_text_relationship_map(
    results: list[dict[str, Any]],
    show_external: bool = True,
) -> str:
    blocks: list[str] = []
    for record in results:
        company_name = record.get("nazev") or "(neznámý název)"
        lines = [company_name]

        address = record.get("sidlo_raw") or record.get("sidlo")
        participant_lines: list[str] = []
        for person in record.get("osoby", []) or []:
            state = classify_relationship_state(
                stav_vazby=person.get("stav_vazby"),
                date_to=person.get("do"),
            ).lower()
            role = person.get("role") or "neuvedeno"
            participant_lines.append(f"Osoba {person.get('jmeno')} – {state} {role}")

        if address:
            participant_lines.append(f"Adresa {address}")

        linked_companies = record.get("navazane_firmy", []) or []
        for linked in linked_companies[:5]:
            if (
                not show_external
                and linked.get("verification_status") == "unverified_external"
            ):
                continue
            linked_name = linked.get("firma")
            if not linked_name:
                continue
            participant_lines.append(
                f"Firma {linked_name} – {linked.get('role') or linked.get('stav_vazby') or 'vazba'}"
            )

        for index, line in enumerate(participant_lines):
            prefix = "└─" if index == len(participant_lines) - 1 else "├─"
            lines.append(f"{prefix} {line}")

        blocks.append("\n".join(lines))

    return "\n\n".join(blocks)


def build_key_nodes(
    shared_people: pd.DataFrame,
    shared_addresses: pd.DataFrame,
    participant_edges: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    people = pd.DataFrame(columns=["Jméno osoby", "Počet vazeb", "Seznam firem"])
    if not shared_people.empty:
        people = (
            shared_people.rename(
                columns={
                    "Počet firem": "Počet vazeb",
                    "Jméno osoby": "Jméno osoby",
                    "Seznam firem": "Seznam firem",
                }
            )[["Jméno osoby", "Počet vazeb", "Seznam firem"]]
            .sort_values(["Počet vazeb", "Jméno osoby"], ascending=[False, True])
            .head(10)
        )

    addresses = pd.DataFrame(columns=["Adresa", "Počet vazeb", "Seznam firem"])
    if not shared_addresses.empty:
        addresses = (
            shared_addresses.rename(columns={"Počet firem": "Počet vazeb"})
            .sort_values(["Počet vazeb", "Adresa"], ascending=[False, True])
            .head(10)
        )

    companies = pd.DataFrame(columns=["Firma", "Počet vazeb"])
    if not participant_edges.empty:
        companies = (
            participant_edges.groupby("Firma")
            .agg(**{"Počet vazeb": ("Účastník", "nunique")})
            .reset_index()
            .sort_values(["Počet vazeb", "Firma"], ascending=[False, True])
            .head(10)
        )

    return {
        "people": people,
        "addresses": addresses,
        "companies": companies,
    }


def classify_relationship_state(stav_vazby: Any, date_to: Any) -> str:
    status = str(stav_vazby or "").strip().lower()
    if date_to:
        return "Historická"
    if any(marker in status for marker in ["histor", "býval", "zanikl", "ukončen"]):
        return "Historická"
    return "Aktuální"


def summarize_relationship_states(states: list[str]) -> str:
    unique_states = sorted(set(states))
    if unique_states == ["Aktuální"]:
        return "Aktuální"
    if unique_states == ["Historická"]:
        return "Historická"
    if "Aktuální" in unique_states and "Historická" in unique_states:
        return "Aktuální i historická"
    return ", ".join(unique_states) if unique_states else "neuvedeno"


def render_relationship_section(
    title: str,
    dataframe: pd.DataFrame,
    empty_text: str,
    use_html: bool = False,
) -> None:
    st.markdown(f"### {title}", unsafe_allow_html=use_html)
    if dataframe.empty:
        st.info(empty_text)
        return
    st.dataframe(dataframe, use_container_width=True)


def render_small_table(dataframe: pd.DataFrame, empty_text: str) -> None:
    if dataframe.empty:
        st.caption(empty_text)
        return
    st.dataframe(
        dataframe,
        use_container_width=True,
        height=min(420, 60 + 35 * len(dataframe)),
    )


def render_source_diagnostics(results: list[dict[str, Any]]) -> None:
    with st.expander("Diagnostika zdrojů", expanded=False):
        rows: list[dict[str, Any]] = []
        for record in results:
            diagnostics = record.get("source_diagnostics") or {}
            counts = diagnostics.get("counts") or {}
            relationship_diagnostics = record.get("relationship_diagnostics") or {}
            rows.append(
                {
                    "IČO": record.get("ico"),
                    "ARES": relationship_diagnostics.get("ares", 0),
                    "Justice": relationship_diagnostics.get("justice", 0),
                    "Kurzy": relationship_diagnostics.get("kurzy", 0),
                    "Sloučeno": relationship_diagnostics.get("merged", 0),
                    "Vynecháno": relationship_diagnostics.get("skipped", 0),
                    "Ověřené vazby": counts.get("verified_relationships", 0),
                    "Externí vazby": counts.get("unverified_external_relationships", 0),
                    "Bez IČO": counts.get("pending_ico_relationships", 0),
                    "Chyby zdrojů": counts.get("source_errors", 0),
                }
            )
            for warning in diagnostics.get("parser_warnings") or []:
                st.warning(f"{record.get('ico')}: {warning}")

        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True)
        else:
            st.info("Diagnostika zdrojů není k dispozici.")


def render_cross_analysis_inputs() -> tuple[bool, str, str]:
    st.caption(
        "Zadej osoby a případně další IČA firem. Program pak vyhodnotí společné "
        "adresy, jednatele, společníky a prokuru. Skutečné majitele připraví k ručnímu ověření."
    )
    analysis_col1, analysis_col2 = st.columns(2)
    with analysis_col1:
        cross_people_text = st.text_area(
            "Osoby pro analýzu",
            height=100,
            key="cross_people_text",
            placeholder="Osoba 1\nOsoba 2",
        )
    with analysis_col2:
        cross_ico_text = st.text_area(
            "Další IČA firem pro analýzu",
            height=100,
            key="cross_ico_text",
            placeholder="12345678\n87654321",
        )

    run_cross_analysis = st.button(
        "🚀 Spustit porovnání všech zadaných osob a firem",
        use_container_width=True,
    )
    return run_cross_analysis, cross_people_text, cross_ico_text


def render_cross_analysis_results(
    cross_analysis: dict[str, pd.DataFrame],
    cross_analysis_summary: pd.DataFrame,
) -> None:
    st.markdown("**Je mezi všemi zadanými spojitost?**")
    st.dataframe(cross_analysis_summary, use_container_width=True)
    st.markdown("**Firmy zahrnuté do této analýzy:**")
    st.dataframe(cross_analysis["firmy"], use_container_width=True)
    st.markdown("**Společné adresy:**")
    if cross_analysis["spolecne_adresy"].empty:
        st.write("Nebyla nalezena žádná adresa sdílená více než jedním subjektem.")
    else:
        st.dataframe(cross_analysis["spolecne_adresy"], use_container_width=True)
    st.markdown("**Společní jednatelé:**")
    if cross_analysis["spolecni_jednatele"].empty:
        st.write("Nebyl nalezen žádný společný jednatel v načtených firmách.")
    else:
        st.dataframe(cross_analysis["spolecni_jednatele"], use_container_width=True)
    st.markdown("**Společní společníci:**")
    if cross_analysis["spolecni_spolecnici"].empty:
        st.write("Nebyl nalezen žádný společný společník v načtených firmách.")
    else:
        st.dataframe(cross_analysis["spolecni_spolecnici"], use_container_width=True)
    st.markdown("**Osoby s plnou mocí / prokurou:**")
    if cross_analysis["osoby_s_plnou_moci"].empty:
        st.write("Nebyla nalezena žádná osoba s prokurou nebo obdobným oprávněním v načtených datech.")
    else:
        st.dataframe(cross_analysis["osoby_s_plnou_moci"], use_container_width=True)
    st.markdown("**Skuteční majitelé – ruční ověření:**")
    st.dataframe(cross_analysis["skutecni_majitele_manual"], use_container_width=True)


def render_relationships_controls() -> tuple[str, bool, bool]:
    st.caption("Přidej další firmy do případu a rozšiř síť vztahů napříč načtenými subjekty.")
    extra_ico_text = st.text_area(
        "Další IČA pro rozšíření vztahů",
        height=90,
        key="extra_relationship_ico_text",
        placeholder="Zadej další IČA, která chceš přidat k porovnání vztahů.",
    )
    auto_include_all_entities_extra = st.checkbox(
        "Při přidání dalších firem zahrnout do vazeb všechny jejich osoby i navázané firmy",
        key="auto_include_all_entities_extra",
    )
    add_relationship_companies = st.button(
        "➕ Přidat další firmy do vztahů",
        use_container_width=True,
    )

    return (extra_ico_text, auto_include_all_entities_extra, add_relationship_companies)


def render_selected_people_results(
    selected_people_names: list[str],
    selected_people_rows: list[dict[str, Any]],
    intersections: dict[str, Any],
    relationship_include_all_entities: bool,
    include_historical: bool,
) -> None:
    if selected_people_names:
        st.markdown("**Vybrané osoby:**")
        if selected_people_rows:
            st.dataframe(pd.DataFrame(selected_people_rows), use_container_width=True)

        st.markdown("**Výskyty vybraných osob napříč načtenými firmami:**")
        if intersections["selected_occurrences"].empty:
            st.write("U vybraných osob se nepodařilo dohledat žádné výskyty v aktuálně načtených datech.")
        else:
            st.dataframe(intersections["selected_occurrences"], use_container_width=True)

        st.markdown("**Firmy, kde se vybrané osoby objevují:**")
        if intersections["selected_companies"].empty:
            st.write("Nebyla nalezena žádná firma s výskytem vybraných osob.")
        else:
            st.dataframe(intersections["selected_companies"], use_container_width=True)

        if relationship_include_all_entities:
            st.markdown("**Všechny osoby a navázané firmy zahrnuté do vazeb:**")
            if intersections["relationship_graph"]["participant_edges"].empty:
                st.write("Pro aktuálně načtené firmy se nepodařilo sestavit žádné vazby účastníků.")
            else:
                st.dataframe(
                    intersections["relationship_graph"]["participant_edges"],
                    use_container_width=True,
                )

            st.markdown("**Společné osoby a firmy napříč načtenými firmami:**")
            if intersections["shared_participants"].empty:
                st.write("Mezi aktuálně načtenými firmami nebyly nalezeny žádné opakující se osoby ani firmy.")
            else:
                st.dataframe(intersections["shared_participants"], use_container_width=True)

        st.markdown("**Další dohledání vazeb vybraných osob:**")
        for person_name in selected_people_names:
            st.markdown(
                f"- 👤 {person_name}: "
                f"[vyhledat vazby v Kurzy.cz]({format_kurzy_search_link(person_name, not include_historical)})"
            )
    else:
        st.info("Zaklikni osoby ve firmách a spusť prověření vazeb.")
