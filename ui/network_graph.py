"""Interaktivní graf vazeb nad již načtenými výsledky."""

from typing import Any

import streamlit as st
from streamlit_agraph import Config, Edge, Node, agraph

from analysis.graph import (
    build_visual_relationship_dataset,
    filter_visual_relationship_dataset,
)

NODE_COLORS = {
    "company": "#2563EB",
    "candidate_company": "#94A3B8",
    "person": "#16A34A",
    "address": "#F59E0B",
    "risk": "#DC2626",
    "group_company": "#93C5FD",
    "group_person": "#86EFAC",
}

EDGE_COLORS = {
    "jednatel": "#2563EB",
    "společník": "#16A34A",
    "vlastník": "#0F766E",
    "plná moc": "#7C3AED",
    "historická vazba": "#94A3B8",
    "sdílená adresa": "#F59E0B",
    "adresa": "#FBBF24",
    "rizikový signál": "#DC2626",
}


@st.cache_data(show_spinner=False)
def get_cached_graph_dataset(results: list[dict[str, Any]]) -> dict[str, Any]:
    return build_visual_relationship_dataset(results)


def render_graph_screen(
    results: list[dict[str, Any]],
    relationship_graph: dict[str, Any] | None,
) -> None:
    del relationship_graph

    st.subheader("Graf vazeb")
    st.caption("Síť firem, osob, adres a rizikových signálů z právě načtených dat.")

    base_graph = get_cached_graph_dataset(results)
    render_graph_filters()

    filtered_graph = filter_visual_relationship_dataset(
        base_graph,
        show_companies=st.session_state.get("graph_show_companies", True),
        show_people=st.session_state.get("graph_show_people", True),
        show_addresses=st.session_state.get("graph_show_addresses", True),
        show_historical=st.session_state.get("graph_show_historical", True),
        show_risks=st.session_state.get("graph_show_risks", True),
        show_external=st.session_state.get("graph_show_external", True),
    )

    render_graph_stats(filtered_graph)
    render_graph_aggregation_notice(filtered_graph)
    render_graph_controls()

    graph_col, detail_col = st.columns([3.2, 1.2], gap="large")
    with graph_col:
        selected_node = render_interactive_graph(filtered_graph)
    with detail_col:
        render_selected_node_detail(selected_node, filtered_graph)


def render_graph_filters() -> None:
    st.markdown("### Filtry")
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    with col1:
        st.checkbox("🏢 Firmy", value=True, key="graph_show_companies")
    with col2:
        st.checkbox("👤 Osoby", value=True, key="graph_show_people")
    with col3:
        st.checkbox("📍 Adresy", value=True, key="graph_show_addresses")
    with col4:
        st.checkbox(
            "🕰 Historické vazby",
            value=True,
            key="graph_show_historical",
            help="Zobrazí i dřívější role a vazby, které už nemusí být aktuální.",
        )
    with col5:
        st.checkbox("⚠️ Rizikové signály", value=True, key="graph_show_risks")
    with col6:
        st.checkbox(
            "Externí vazby",
            value=True,
            key="graph_show_external",
            help="Zobrazí i vazby z veřejných agregátorů, které je nutné ověřit.",
        )


def render_graph_stats(graph_data: dict[str, Any]) -> None:
    stats = graph_data["stats"]
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Počet firem", stats["companies"])
    with col2:
        st.metric("Počet osob", stats["people"])
    with col3:
        st.metric("Počet adres", stats["addresses"])
    with col4:
        st.metric("Počet vazeb", stats["relationships"])


def render_graph_aggregation_notice(graph_data: dict[str, Any]) -> None:
    aggregated = graph_data.get("aggregated", {})
    hidden_companies = aggregated.get("companies_hidden", 0)
    hidden_people = aggregated.get("people_hidden", 0)
    if not hidden_companies and not hidden_people:
        return

    parts: list[str] = []
    if hidden_companies:
        parts.append(f"{hidden_companies} firem")
    if hidden_people:
        parts.append(f"{hidden_people} osob")
    st.info(
        "Graf byl kvůli přehlednosti automaticky seskupen. "
        f"Skryto do souhrnných uzlů: {', '.join(parts)}."
    )


def render_graph_controls() -> None:
    st.markdown("### Ovládání grafu")
    if "graph_zoom_level" not in st.session_state:
        st.session_state["graph_zoom_level"] = 1.0

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🔍 Přiblížit", use_container_width=True):
            st.session_state["graph_zoom_level"] = min(
                1.6, st.session_state["graph_zoom_level"] + 0.15
            )
            st.rerun()
    with col2:
        if st.button("🔎 Oddálit", use_container_width=True):
            st.session_state["graph_zoom_level"] = max(
                0.7, st.session_state["graph_zoom_level"] - 0.15
            )
            st.rerun()
    with col3:
        if st.button("🎯 Vycentrovat graf", use_container_width=True):
            st.session_state["graph_zoom_level"] = 1.0
            st.session_state["graph_selected_node_id"] = None
            st.rerun()

    st.caption("Graf lze také posouvat myší a přibližovat kolečkem.")


def render_interactive_graph(graph_data: dict[str, Any]) -> str | None:
    if not graph_data["nodes"] or not graph_data["edges"]:
        st.info("Pro zadané filtry teď není k dispozici žádná síť vazeb.")
        return None

    selected_node_id = st.session_state.get("graph_selected_node_id")
    if selected_node_id and selected_node_id not in {node["id"] for node in graph_data["nodes"]}:
        selected_node_id = None
        st.session_state["graph_selected_node_id"] = None

    adjacent_ids = build_adjacent_node_ids(selected_node_id, graph_data["edges"])
    zoom_level = st.session_state.get("graph_zoom_level", 1.0)

    nodes = [
        Node(
            id=node["id"],
            label=build_node_label(node),
            title=build_node_title(node),
            color=resolve_node_color(node, selected_node_id, adjacent_ids),
            size=resolve_node_size(node, zoom_level, selected_node_id, adjacent_ids),
            shape="dot",
            font={"size": int(14 * zoom_level), "face": "Inter, sans-serif"},
        )
        for node in graph_data["nodes"]
    ]

    edges = [
        Edge(
            source=edge["source"],
            target=edge["target"],
            label=edge["label"],
            color=resolve_edge_color(edge, selected_node_id, adjacent_ids),
            width=resolve_edge_width(edge, selected_node_id, adjacent_ids),
            dashes=edge.get("historical", False)
            or edge.get("meta", {}).get("unverified_external", False),
            smooth={"type": "dynamic"},
            font={"size": 11, "align": "middle"},
        )
        for edge in graph_data["edges"]
    ]

    config = Config(
        width=860,
        height=720,
        directed=False,
        physics=len(graph_data["nodes"]) < 850,
        hierarchical=False,
        nodeHighlightBehavior=True,
        highlightColor="#DBEAFE",
        collapsible=False,
        link={"labelProperty": "label", "renderLabel": True},
        interaction={
            "hover": True,
            "tooltipDelay": 150,
            "navigationButtons": True,
            "keyboard": {"enabled": True, "bindToWindow": False},
            "zoomView": True,
            "dragView": True,
        },
        nodes={
            "shadow": True,
            "borderWidth": 1,
            "borderWidthSelected": 3,
        },
        edges={
            "smooth": {"type": "dynamic"},
            "selectionWidth": 2.5,
        },
        stabilization=True,
        fit=True,
    )

    clicked_node = agraph(nodes=nodes, edges=edges, config=config)
    if clicked_node:
        st.session_state["graph_selected_node_id"] = clicked_node
        return clicked_node
    return selected_node_id


def build_adjacent_node_ids(
    selected_node_id: str | None,
    edges: list[dict[str, Any]],
) -> set[str]:
    if not selected_node_id:
        return set()
    adjacent_ids = {selected_node_id}
    for edge in edges:
        if edge["source"] == selected_node_id:
            adjacent_ids.add(edge["target"])
        if edge["target"] == selected_node_id:
            adjacent_ids.add(edge["source"])
    return adjacent_ids


def resolve_node_color(
    node: dict[str, Any],
    selected_node_id: str | None,
    adjacent_ids: set[str],
) -> str:
    base_color = NODE_COLORS.get(node["type"], "#94A3B8")
    if not selected_node_id:
        return base_color
    if node["id"] in adjacent_ids:
        return base_color
    return "#CBD5E1"


def resolve_node_size(
    node: dict[str, Any],
    zoom_level: float,
    selected_node_id: str | None,
    adjacent_ids: set[str],
) -> int:
    meta = node.get("meta", {})
    degree_hint = meta.get("company_count", 1)
    base_size = 18
    if node["type"] in {"company", "candidate_company"}:
        base_size = 26
    elif node["type"] == "person":
        base_size = 18 + min(degree_hint, 5)
    elif node["type"] == "address":
        base_size = 16 + min(degree_hint, 4)
    elif node["type"] == "risk":
        base_size = 14

    if selected_node_id and node["id"] in adjacent_ids:
        base_size += 4
    return int(base_size * zoom_level)


def resolve_edge_color(
    edge: dict[str, Any],
    selected_node_id: str | None,
    adjacent_ids: set[str],
) -> str:
    base_color = EDGE_COLORS.get(edge["type"], "#64748B")
    if not selected_node_id:
        return base_color
    if edge["source"] in adjacent_ids and edge["target"] in adjacent_ids:
        return base_color
    return "#CBD5E1"


def resolve_edge_width(
    edge: dict[str, Any],
    selected_node_id: str | None,
    adjacent_ids: set[str],
) -> float:
    width = 2.0
    if edge.get("count", 1) > 1:
        width = min(6.0, 2.0 + edge["count"] * 0.2)
    if selected_node_id and edge["source"] in adjacent_ids and edge["target"] in adjacent_ids:
        width += 1.0
    return width


def build_node_label(node: dict[str, Any]) -> str:
    label = node["label"]
    if node["type"] == "risk":
        return "⚠️ Riziko"
    if node["type"] == "group_company":
        return node["label"]
    if node["type"] == "group_person":
        return node["label"]
    if len(label) > 28:
        return f"{label[:25]}..."
    return label


def build_node_title(node: dict[str, Any]) -> str:
    meta = node.get("meta", {})
    if node["type"] in {"company", "candidate_company"}:
        verification = meta.get("verification_label") or meta.get("verification_status") or "—"
        return (
            f"{meta.get('name')}\\nIČO: {meta.get('ico') or '—'}"
            f"\\nSídlo: {meta.get('address') or '—'}\\nOvěření: {verification}"
        )
    if node["type"] == "person":
        return (
            f"{meta.get('name')}\\nRole: {', '.join(meta.get('roles') or ['neuvedeno'])}"
            f"\\nPočet firem: {meta.get('company_count') or 0}"
        )
    if node["type"] == "address":
        return (
            f"{meta.get('address')}\\nPočet firem: {meta.get('company_count') or 0}"
        )
    if node["type"] == "risk":
        return f"{meta.get('signal')}\\nZdroj: {meta.get('source') or 'nutno ověřit'}"
    if node["type"] == "group_company":
        return node["label"]
    if node["type"] == "group_person":
        return node["label"]
    return node["label"]


def render_selected_node_detail(
    selected_node_id: str | None,
    graph_data: dict[str, Any],
) -> None:
    st.markdown("### Detail uzlu")
    if not selected_node_id:
        st.info("Klikni na uzel v grafu a zobrazí se jeho detail.")
        return

    node_map = {node["id"]: node for node in graph_data["nodes"]}
    node = node_map.get(selected_node_id)
    if not node:
        st.info("Vybraný uzel není v aktuálním filtru.")
        return

    node_type = node["type"]
    meta = node.get("meta", {})

    if node_type in {"company", "candidate_company"}:
        st.markdown("**🏢 Firma**")
        st.write(meta.get("name") or "—")
        st.caption(f"IČO: {meta.get('ico') or '—'}")
        st.write(f"Sídlo: {meta.get('address') or '—'}")
        if node_type == "candidate_company":
            st.warning("Externí vazba bez plného ověření. Nutno ověřit ručně.")
        if meta.get("source_url"):
            st.markdown(f"[Ověřit zdroj]({meta.get('source_url')})")
        if meta.get("risk_level"):
            st.write(f"Riziková úroveň: {meta.get('risk_level')}")
        return

    if node_type == "person":
        st.markdown("**👤 Osoba**")
        st.write(meta.get("name") or "—")
        st.write(f"Role: {', '.join(meta.get('roles') or ['neuvedeno'])}")
        st.write(f"Počet firem: {meta.get('company_count') or 0}")
        if meta.get("companies"):
            st.write("Firmy:")
            for company_name in meta["companies"][:12]:
                st.caption(company_name)
        return

    if node_type == "address":
        st.markdown("**📍 Adresa**")
        st.write(meta.get("address") or node["label"])
        companies = meta.get("companies") or []
        if companies:
            st.write("Firmy:")
            for company_name in companies[:15]:
                st.caption(company_name)
        return

    if node_type == "risk":
        st.markdown("**⚠️ Rizikový signál**")
        st.write(meta.get("signal") or "—")
        st.write(f"Subjekt: {meta.get('company_name') or '—'}")
        st.write(f"Závažnost: {meta.get('certainty') or 'nutno ověřit'}")
        if meta.get("source"):
            st.markdown(f"[Zdroj / ověření]({meta['source']})")
        return

    if node_type == "group_company":
        st.markdown("**🏢 Seskupené firmy**")
        for company_name in (meta.get("companies") or [])[:20]:
            st.caption(company_name)
        return

    if node_type == "group_person":
        st.markdown("**👤 Seskupené osoby**")
        for person_name in (meta.get("people") or [])[:20]:
            st.caption(person_name)
        return

    st.write(node["label"])
