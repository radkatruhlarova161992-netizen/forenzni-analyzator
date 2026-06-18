"""Vysvětlivky a jednoduché UX helpery pro běžného uživatele."""

from typing import Any

import streamlit as st

TERM_EXPLANATIONS: dict[str, str] = {
    "jednatel": "Osoba, která jedná jménem firmy a zastupuje ji navenek.",
    "společník": "Osoba nebo firma, která má ve společnosti podíl.",
    "historická vazba": "Vazba, která v minulosti existovala, ale podle dostupných dat už nemusí být aktuální.",
    "rizikový signál": "Fakt, který může být důležitý pro kontrolu a je vhodné ho ověřit ručně.",
    "likvidace": "Proces ukončování firmy, kdy se vypořádává její majetek a závazky.",
    "fúze": "Spojení dvou nebo více firem do jedné struktury.",
}


def tooltip_term(term: str) -> str:
    explanation = TERM_EXPLANATIONS.get(term.lower(), "")
    if not explanation:
        return term
    return (
        f'<span title="{explanation}" '
        "style=\"border-bottom:1px dotted #6b7280; cursor: help;\">"
        f"{term}</span>"
    )


def render_term_tooltips() -> None:
    st.markdown("### Pojmy")
    chips = [
        f'<span title="{explanation}" '
        "style=\"display:inline-block; margin:0 8px 8px 0; padding:6px 10px; "
        "border-radius:8px; background:#f3f4f6; color:#111827; font-size:0.92rem; cursor:help;\">"
        f"{term}</span>"
        for term, explanation in TERM_EXPLANATIONS.items()
    ]
    st.markdown("".join(chips), unsafe_allow_html=True)


def render_info_card(title: str, body: str, tone: str) -> None:
    colors = {
        "company": ("#ecfeff", "#0f766e"),
        "historical": ("#fff7ed", "#c2410c"),
        "person": ("#eff6ff", "#1d4ed8"),
        "address": ("#f0fdf4", "#15803d"),
        "risk": ("#fef2f2", "#b91c1c"),
    }
    background, accent = colors.get(tone, ("#f9fafb", "#374151"))
    st.markdown(
        (
            f'<div style="background:{background}; border-left:4px solid {accent}; '
            'padding:12px 14px; border-radius:8px; margin-bottom:10px;">'
            f'<div style="font-weight:600; color:{accent}; margin-bottom:4px;">{title}</div>'
            f'<div style="color:#111827;">{body}</div>'
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def render_key_findings_intro(results: list[dict[str, Any]]) -> None:
    st.markdown("### Nejdůležitější nálezy")
    repeated_people = count_repeated_people(results)
    repeated_addresses = count_repeated_addresses(results)
    liquidations = sum(1 for record in results if record.get("v_likvidaci"))
    risk_records = sum(1 for record in results if record.get("risk_flags"))

    render_info_card(
        "Nalezené firmy",
        f"V analýze je nyní {len(results)} firemních subjektů.",
        "company",
    )
    if repeated_people:
        render_info_card(
            "Společná osoba",
            f"Ve více firmách se opakuje {repeated_people} osob.",
            "person",
        )
    if repeated_addresses:
        render_info_card(
            "Společná adresa",
            f"Ve více firmách se opakuje {repeated_addresses} adres.",
            "address",
        )
    if liquidations:
        render_info_card(
            "Historická nebo ukončovaná vazba",
            f"U {liquidations} subjektů je vidět {tooltip_term('likvidace')}.",
            "historical",
        )
    if risk_records:
        render_info_card(
            "Rizikový signál",
            f"U {risk_records} subjektů byl zachycen alespoň jeden {tooltip_term('rizikový signál')}.",
            "risk",
        )


def render_meaning_section() -> None:
    st.markdown("### Co to znamená?")
    st.write(
        "Výsledky ukazují veřejně dohledané vazby mezi firmami, osobami a adresami. "
        "Nejde o závěr, ale o podklady k ověření."
    )
    st.markdown(
        "- Opakující se osoba může znamenat společné řízení nebo vlastnickou vazbu.\n"
        "- Společná adresa může znamenat stejný kontakt, sídlo nebo servisní firmu.\n"
        "- Historická vazba ukazuje, že propojení existovalo v minulosti.\n"
        "- Rizikový signál je upozornění na údaj, který stojí za kontrolu."
    )


def render_next_steps_section() -> None:
    st.markdown("### Doporučené další kroky")
    st.markdown(
        "1. Otevři obrazovku **Firmy** a zkontroluj základní údaje a zdroje.\n"
        "2. Na obrazovce **Osoby** si vyfiltruj opakující se osoby.\n"
        "3. Na obrazovce **Vazby** porovnej společné osoby, adresy a historické vazby.\n"
        "4. U **Rizik** otevři zdroj a ověř, jestli je údaj stále platný."
    )


def count_repeated_people(results: list[dict[str, Any]]) -> int:
    people_map: dict[str, set[str]] = {}
    for record in results:
        for person in record.get("osoby", []) or []:
            if person.get("jmeno"):
                people_map.setdefault(person["jmeno"], set()).add(record.get("ico", ""))
    return sum(1 for companies in people_map.values() if len(companies) > 1)


def count_repeated_addresses(results: list[dict[str, Any]]) -> int:
    address_map: dict[str, set[str]] = {}
    for record in results:
        address = record.get("sidlo_raw") or record.get("sidlo")
        if address:
            address_map.setdefault(address, set()).add(record.get("ico", ""))
    return sum(1 for companies in address_map.values() if len(companies) > 1)
