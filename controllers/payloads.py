"""Příprava payloadů pro UI."""

from typing import Any

from analysis.graph import build_relationship_graph, find_intersections


def build_ui_payloads(
    results: list[dict[str, Any]],
    selected_people_names: list[str],
    selected_people_rows: list[dict[str, Any]],
    relationship_include_all_entities: bool,
    cross_analysis_people: list[str],
    cross_analysis_enabled: bool,
) -> dict[str, Any]:
    relationship_graph = build_relationship_graph(results) if results else None
    all_intersections = None

    if results and relationship_graph:
        all_intersections = find_intersections(
            results,
            relationship_graph,
            selected_people_names=selected_people_names,
            input_people=cross_analysis_people,
        )
        all_intersections["relationship_graph"] = relationship_graph

    cross_analysis_payload = None
    if all_intersections and cross_analysis_enabled:
        cross_analysis_payload = {
            "cross_analysis": all_intersections["cross_analysis"],
            "cross_analysis_summary": all_intersections["cross_analysis_summary"],
        }

    selected_people_payload = None
    if all_intersections:
        selected_people_payload = {
            "selected_people_names": selected_people_names,
            "selected_people_rows": selected_people_rows,
            "relationship_include_all_entities": relationship_include_all_entities,
            "intersections": all_intersections,
        }

    return {
        "relationship_graph": relationship_graph,
        "all_intersections": all_intersections,
        "cross_analysis_payload": cross_analysis_payload,
        "selected_people_payload": selected_people_payload,
    }
