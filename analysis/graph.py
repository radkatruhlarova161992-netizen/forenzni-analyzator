"""Analýza vazeb mezi firmami a osobami."""

from typing import Any

import pandas as pd

from core.utils import format_kurzy_search_link, normalize_name


def find_person_overlaps(records: list[dict[str, Any]]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for rec in records:
        for osoba in rec.get("osoby", []) or []:
            rows.append(
                {
                    "Osoba": osoba["jmeno"],
                    "Role": osoba["role"],
                    "Firma": rec.get("nazev") or "(neznámý název)",
                    "IČO": rec.get("ico"),
                    "Od": osoba.get("od"),
                    "Do": osoba.get("do"),
                }
            )

    if not rows:
        return pd.DataFrame(columns=["Osoba", "Role", "Firma", "IČO", "Od", "Do"])

    return pd.DataFrame(rows)


def summarize_overlapping_persons(person_df: pd.DataFrame) -> pd.DataFrame:
    if person_df.empty:
        return pd.DataFrame(columns=["Osoba", "Počet firem", "Firmy"])

    grouped = person_df.groupby("Osoba").agg(
        **{
            "Počet firem": ("IČO", "nunique"),
            "Firmy": ("Firma", lambda x: ", ".join(sorted(set(x)))),
        }
    ).reset_index()
    return grouped[grouped["Počet firem"] > 1].sort_values("Počet firem", ascending=False)


def find_company_links(records: list[dict[str, Any]]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for rec in records:
        for company in rec.get("navazane_firmy", []) or []:
            rows.append(
                {
                    "Výchozí firma": rec.get("nazev") or "(neznámý název)",
                    "Výchozí IČO": rec.get("ico"),
                    "Navázaná firma": company.get("firma"),
                    "Navázané IČO": company.get("ico"),
                    "Role": company.get("role"),
                    "Stav vazby": company.get("stav_vazby"),
                    "Od": company.get("od"),
                    "Do": company.get("do"),
                }
            )

    if not rows:
        return pd.DataFrame(
            columns=[
                "Výchozí firma",
                "Výchozí IČO",
                "Navázaná firma",
                "Navázané IČO",
                "Role",
                "Stav vazby",
                "Od",
                "Do",
            ]
        )

    return pd.DataFrame(rows)


def build_relationship_graph(records: list[dict[str, Any]]) -> dict[str, pd.DataFrame]:
    """Vytvoří jednotný graf vztahů pro další průniky a výpisy v UI."""
    person_occurrences = find_person_overlaps(records)
    company_links = find_company_links(records)
    participant_edges = build_participant_edges(records)
    return {
        "person_occurrences": person_occurrences,
        "company_links": company_links,
        "participant_edges": participant_edges,
    }


def build_participant_edges(records: list[dict[str, Any]]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for rec in records:
        company_name = rec.get("nazev") or "(neznámý název)"
        company_ico = rec.get("ico")

        for person in rec.get("osoby", []) or []:
            rows.append(
                {
                    "Firma": company_name,
                    "IČO": company_ico,
                    "Účastník": person.get("jmeno"),
                    "Typ účastníka": "Osoba",
                    "Role": person.get("role"),
                    "Stav vazby": person.get("stav_vazby"),
                    "Od": person.get("od"),
                    "Do": person.get("do"),
                }
            )

        for linked_company in rec.get("navazane_firmy", []) or []:
            participant_name = linked_company.get("firma")
            participant_ico = linked_company.get("ico")
            if participant_name:
                rows.append(
                    {
                        "Firma": company_name,
                        "IČO": company_ico,
                        "Účastník": (
                            f"{participant_name} ({participant_ico})"
                            if participant_ico
                            else participant_name
                        ),
                        "Typ účastníka": "Firma",
                        "Role": linked_company.get("role"),
                        "Stav vazby": linked_company.get("stav_vazby"),
                        "Od": linked_company.get("od"),
                        "Do": linked_company.get("do"),
                    }
                )

    if not rows:
        return pd.DataFrame(
            columns=["Firma", "IČO", "Účastník", "Typ účastníka", "Role", "Stav vazby", "Od", "Do"]
        )

    return pd.DataFrame(rows)


def summarize_shared_participants(edges_df: pd.DataFrame) -> pd.DataFrame:
    if edges_df.empty:
        return pd.DataFrame(columns=["Účastník", "Typ účastníka", "Počet firem", "Firmy", "Role"])

    grouped = (
        edges_df.groupby(["Účastník", "Typ účastníka"])
        .agg(
            **{
                "Počet firem": ("IČO", "nunique"),
                "Firmy": ("Firma", lambda x: ", ".join(sorted(set(x)))),
                "Role": ("Role", lambda x: ", ".join(sorted(set(filter(None, x))))),
            }
        )
        .reset_index()
    )
    return grouped[grouped["Počet firem"] > 1].sort_values(
        ["Počet firem", "Účastník"], ascending=[False, True]
    )


def build_selected_people_occurrences(
    records: list[dict[str, Any]],
    selected_people_names: list[str],
) -> pd.DataFrame:
    if not selected_people_names:
        return pd.DataFrame(
            columns=["Osoba", "Firma", "IČO", "Role", "Stav vazby", "Od", "Do", "Kurzy.cz"]
        )

    rows: list[dict[str, Any]] = []
    selected_set = set(selected_people_names)
    for rec in records:
        for person in rec.get("osoby", []) or []:
            if person.get("jmeno") not in selected_set:
                continue
            rows.append(
                {
                    "Osoba": person.get("jmeno"),
                    "Firma": rec.get("nazev") or "(neznámý název)",
                    "IČO": rec.get("ico"),
                    "Role": person.get("role"),
                    "Stav vazby": person.get("stav_vazby"),
                    "Od": person.get("od"),
                    "Do": person.get("do"),
                    "Kurzy.cz": person.get("kurzy_vazby_link"),
                }
            )

    if not rows:
        return pd.DataFrame(
            columns=["Osoba", "Firma", "IČO", "Role", "Stav vazby", "Od", "Do", "Kurzy.cz"]
        )

    return pd.DataFrame(rows)


def summarize_selected_people_companies(occurrence_df: pd.DataFrame) -> pd.DataFrame:
    if occurrence_df.empty:
        return pd.DataFrame(columns=["Firma", "IČO", "Vybrané osoby", "Počet vybraných osob"])

    return (
        occurrence_df.groupby(["Firma", "IČO"])
        .agg(
            **{
                "Vybrané osoby": ("Osoba", lambda x: ", ".join(sorted(set(x)))),
                "Počet vybraných osob": ("Osoba", "nunique"),
            }
        )
        .reset_index()
        .sort_values(["Počet vybraných osob", "Firma"], ascending=[False, True])
    )


def role_matches(person: dict[str, Any], keyword: str) -> bool:
    role = str(person.get("role") or "").lower()
    source = str(person.get("zdroj_cast") or "").lower()
    return keyword in role or keyword in source


def build_cross_entity_analysis(
    records: list[dict[str, Any]],
    input_people: list[str],
) -> dict[str, pd.DataFrame]:
    normalized_people = {normalize_name(name): name for name in input_people}
    company_rows: list[dict[str, Any]] = []
    address_rows: list[dict[str, Any]] = []
    jednatele_rows: list[dict[str, Any]] = []
    spolecnici_rows: list[dict[str, Any]] = []
    prokura_rows: list[dict[str, Any]] = []
    manual_owner_rows: list[dict[str, Any]] = []

    for rec in records:
        company_name = rec.get("nazev") or "(neznámý název)"
        company_ico = rec.get("ico")
        company_rows.append({"Firma": company_name, "IČO": company_ico})

        company_address = rec.get("sidlo_raw") or rec.get("sidlo")
        if company_address:
            address_rows.append(
                {
                    "Adresa": company_address,
                    "Typ": "Sídlo firmy",
                    "Subjekt": company_name,
                    "IČO": company_ico,
                }
            )

        manual_owner_rows.append(
            {
                "Firma": company_name,
                "IČO": company_ico,
                "Ruční ověření": format_kurzy_search_link(company_ico or company_name, True),
                "Poznámka": "Skutečné majitele nelze z ARES VR spolehlivě vytáhnout automaticky.",
            }
        )

        for person in rec.get("osoby", []) or []:
            normalized_person_name = normalize_name(person.get("jmeno"))
            tracked_person = normalized_person_name in normalized_people if normalized_people else True

            if person.get("adresa"):
                address_rows.append(
                    {
                        "Adresa": person.get("adresa"),
                        "Typ": "Adresa osoby",
                        "Subjekt": person.get("jmeno"),
                        "IČO": company_ico,
                    }
                )

            if tracked_person and "jednatel" in str(person.get("role") or "").lower():
                jednatele_rows.append(
                    {
                        "Osoba": person.get("jmeno"),
                        "Firma": company_name,
                        "IČO": company_ico,
                        "Role": person.get("role"),
                        "Stav vazby": person.get("stav_vazby"),
                    }
                )

            if tracked_person and role_matches(person, "společník"):
                spolecnici_rows.append(
                    {
                        "Osoba": person.get("jmeno"),
                        "Firma": company_name,
                        "IČO": company_ico,
                        "Role": person.get("role"),
                        "Stav vazby": person.get("stav_vazby"),
                    }
                )

            if tracked_person and (
                "prokur" in str(person.get("role") or "").lower()
                or "prokura" in str(person.get("zdroj_cast") or "").lower()
            ):
                prokura_rows.append(
                    {
                        "Osoba": person.get("jmeno"),
                        "Firma": company_name,
                        "IČO": company_ico,
                        "Role": person.get("role"),
                        "Stav vazby": person.get("stav_vazby"),
                    }
                )

    company_df = pd.DataFrame(company_rows).drop_duplicates()

    address_df = pd.DataFrame(address_rows)
    if not address_df.empty:
        address_df = (
            address_df.groupby("Adresa")
            .agg(
                **{
                    "Počet subjektů": ("Subjekt", "nunique"),
                    "Subjekty": ("Subjekt", lambda x: ", ".join(sorted(set(x)))),
                    "Typy": ("Typ", lambda x: ", ".join(sorted(set(x)))),
                }
            )
            .reset_index()
        )
        address_df = address_df[address_df["Počet subjektů"] > 1].sort_values(
            ["Počet subjektů", "Adresa"], ascending=[False, True]
        )

    def summarize_people(rows: list[dict[str, Any]], column_name: str) -> pd.DataFrame:
        df = pd.DataFrame(rows)
        if df.empty:
            return df
        return (
            df.groupby(column_name)
            .agg(
                **{
                    "Počet firem": ("IČO", "nunique"),
                    "Firmy": ("Firma", lambda x: ", ".join(sorted(set(x)))),
                    "Role": ("Role", lambda x: ", ".join(sorted(set(x)))),
                    "Stavy": ("Stav vazby", lambda x: ", ".join(sorted(set(x)))),
                }
            )
            .reset_index()
            .sort_values(["Počet firem", column_name], ascending=[False, True])
        )

    return {
        "firmy": company_df,
        "spolecne_adresy": address_df if not address_df.empty else pd.DataFrame(),
        "spolecni_jednatele": summarize_people(jednatele_rows, "Osoba"),
        "spolecni_spolecnici": summarize_people(spolecnici_rows, "Osoba"),
        "osoby_s_plnou_moci": summarize_people(prokura_rows, "Osoba"),
        "skutecni_majitele_manual": pd.DataFrame(manual_owner_rows).drop_duplicates(),
    }


def build_cross_analysis_summary(cross_analysis: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = [
        {
            "Kategorie": "Společné adresy",
            "Výsledek": "ANO" if not cross_analysis["spolecne_adresy"].empty else "NE",
            "Poznámka": (
                f"Nalezeno {len(cross_analysis['spolecne_adresy'])} společných adres."
                if not cross_analysis["spolecne_adresy"].empty
                else "Nebyla nalezena žádná sdílená adresa."
            ),
        },
        {
            "Kategorie": "Společní jednatelé",
            "Výsledek": "ANO" if not cross_analysis["spolecni_jednatele"].empty else "NE",
            "Poznámka": (
                f"Nalezeno {len(cross_analysis['spolecni_jednatele'])} společných jednatelů."
                if not cross_analysis["spolecni_jednatele"].empty
                else "Nebyl nalezen žádný společný jednatel."
            ),
        },
        {
            "Kategorie": "Společní společníci",
            "Výsledek": "ANO" if not cross_analysis["spolecni_spolecnici"].empty else "NE",
            "Poznámka": (
                f"Nalezeno {len(cross_analysis['spolecni_spolecnici'])} společných společníků."
                if not cross_analysis["spolecni_spolecnici"].empty
                else "Nebyl nalezen žádný společný společník."
            ),
        },
        {
            "Kategorie": "Osoby s plnou mocí / prokurou",
            "Výsledek": "ANO" if not cross_analysis["osoby_s_plnou_moci"].empty else "NE",
            "Poznámka": (
                f"Nalezeno {len(cross_analysis['osoby_s_plnou_moci'])} záznamů pro prokuru nebo obdobné oprávnění."
                if not cross_analysis["osoby_s_plnou_moci"].empty
                else "Nebyla nalezena žádná osoba s prokurou."
            ),
        },
        {
            "Kategorie": "Skuteční majitelé",
            "Výsledek": "RUČNÍ OVĚŘENÍ",
            "Poznámka": "Veřejná data v této aplikaci neumí skutečné majitele spolehlivě ověřit automaticky.",
        },
    ]
    return pd.DataFrame(rows)


def collect_all_people_from_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for rec in records:
        for person in rec.get("osoby", []) or []:
            rows.append(
                {
                    "person_key": (
                        f"{rec.get('ico')}|{person.get('jmeno')}|"
                        f"{person.get('role')}|{person.get('od')}|{person.get('do')}"
                    ),
                    "jmeno": person.get("jmeno"),
                    "role": person.get("role"),
                    "firma": rec.get("nazev") or "(neznámý název)",
                    "ico": rec.get("ico"),
                    "stav_vazby": person.get("stav_vazby"),
                    "kurzy_vazby_link": person.get("kurzy_vazby_link"),
                }
            )
    return rows


def find_intersections(
    records: list[dict[str, Any]],
    relationship_graph: dict[str, pd.DataFrame],
    selected_people_names: list[str] | None = None,
    input_people: list[str] | None = None,
) -> dict[str, Any]:
    """Vrátí připravené průniky pro zobrazení bez jakékoliv UI logiky."""
    selected_people_names = selected_people_names or []
    input_people = input_people or []

    person_occurrences = relationship_graph["person_occurrences"]
    participant_edges = relationship_graph["participant_edges"]

    shared_people = summarize_overlapping_persons(person_occurrences)
    if not shared_people.empty and selected_people_names:
        shared_people = shared_people[shared_people["Osoba"].isin(selected_people_names)]

    selected_occurrences = build_selected_people_occurrences(records, selected_people_names)
    selected_companies = summarize_selected_people_companies(selected_occurrences)
    shared_participants = summarize_shared_participants(participant_edges)
    cross_analysis = build_cross_entity_analysis(records, input_people)
    cross_analysis_summary = build_cross_analysis_summary(cross_analysis)

    return {
        "shared_people": shared_people,
        "selected_occurrences": selected_occurrences,
        "selected_companies": selected_companies,
        "shared_participants": shared_participants,
        "cross_analysis": cross_analysis,
        "cross_analysis_summary": cross_analysis_summary,
    }


def classify_visual_edge_type(role: Any, relationship_state: Any) -> str:
    role_text = str(role or "").strip().lower()
    state_text = str(relationship_state or "").strip().lower()

    if "histor" in state_text:
        return "historická vazba"
    if "jednatel" in role_text:
        return "jednatel"
    if "společník" in role_text or "spolecnik" in role_text:
        return "společník"
    if "vlastník" in role_text or "vlastnik" in role_text or "majitel" in role_text:
        return "vlastník"
    if "prokur" in role_text or "plná moc" in role_text or "plna moc" in role_text:
        return "plná moc"
    return str(role or "vazba")


def build_visual_relationship_dataset(records: list[dict[str, Any]]) -> dict[str, Any]:
    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []
    edge_keys: set[tuple[str, str, str]] = set()
    address_usage: dict[str, set[str]] = {}

    def add_node(node_id: str, node_type: str, label: str, **meta: Any) -> None:
        if node_id not in nodes:
            nodes[node_id] = {
                "id": node_id,
                "type": node_type,
                "label": label,
                "meta": meta,
            }
            return

        existing_meta = nodes[node_id]["meta"]
        for key, value in meta.items():
            if value in (None, "", [], {}):
                continue
            if isinstance(value, list):
                merged = list(dict.fromkeys((existing_meta.get(key) or []) + value))
                existing_meta[key] = merged
            elif isinstance(value, set):
                merged = set(existing_meta.get(key) or set()) | value
                existing_meta[key] = sorted(merged)
            elif key not in existing_meta or existing_meta.get(key) in (None, ""):
                existing_meta[key] = value

    def add_edge(
        source: str,
        target: str,
        label: str,
        edge_type: str,
        historical: bool = False,
        **meta: Any,
    ) -> None:
        source_id, target_id = sorted([source, target])
        edge_key = (source_id, target_id, label)
        if edge_key in edge_keys:
            return
        edge_keys.add(edge_key)
        edges.append(
            {
                "source": source,
                "target": target,
                "label": label,
                "type": edge_type,
                "historical": historical,
                "meta": meta,
            }
        )

    for record in records:
        company_ico = record.get("ico") or "(bez IČO)"
        company_name = record.get("nazev") or "(neznámá firma)"
        company_id = f"company:{company_ico}"
        company_address = record.get("sidlo_raw") or record.get("sidlo")

        add_node(
            company_id,
            "company",
            company_name,
            ico=company_ico,
            name=company_name,
            address=company_address,
            risk_level=record.get("risk_level"),
            company_count=1,
        )

        if company_address:
            address_key = company_address.strip()
            address_id = f"address:{address_key.lower()}"
            address_usage.setdefault(address_key, set()).add(company_id)
            add_node(
                address_id,
                "address",
                address_key,
                address=address_key,
                companies=[company_name],
                company_ids=[company_id],
            )

        for person in record.get("osoby", []) or []:
            person_name = person.get("jmeno")
            if not person_name:
                continue

            person_id = f"person:{normalize_name(person_name)}"
            relationship_state = person.get("stav_vazby") or (
                "Historická" if person.get("do") else "Aktuální"
            )
            role_name = person.get("role") or "vazba"
            edge_type = classify_visual_edge_type(role_name, relationship_state)

            add_node(
                person_id,
                "person",
                person_name,
                name=person_name,
                roles=[role_name],
                companies=[company_name],
                company_ids=[company_id],
                relationship_states=[relationship_state],
                company_count=1,
            )
            add_edge(
                company_id,
                person_id,
                edge_type,
                edge_type,
                historical=edge_type == "historická vazba",
                role=role_name,
                relationship_state=relationship_state,
                date_from=person.get("od"),
                date_to=person.get("do"),
            )

        for linked_company in record.get("navazane_firmy", []) or []:
            linked_name = linked_company.get("firma")
            linked_ico = linked_company.get("ico") or linked_name or "(bez IČO)"
            if not linked_name:
                continue

            linked_id = f"company:{linked_ico}"
            relationship_state = linked_company.get("stav_vazby") or (
                "Historická" if linked_company.get("do") else "Aktuální"
            )
            role_name = linked_company.get("role") or "vazba"
            edge_type = classify_visual_edge_type(role_name, relationship_state)

            add_node(
                linked_id,
                "company",
                linked_name,
                ico=linked_company.get("ico"),
                name=linked_name,
                address=None,
                risk_level=None,
                company_count=1,
            )
            add_edge(
                company_id,
                linked_id,
                edge_type,
                edge_type,
                historical=edge_type == "historická vazba",
                role=role_name,
                relationship_state=relationship_state,
                date_from=linked_company.get("od"),
                date_to=linked_company.get("do"),
            )

        for index, flag in enumerate(record.get("risk_flags", []) or [], start=1):
            signal = flag.get("signal")
            if not signal:
                continue

            risk_id = f"risk:{company_ico}:{index}"
            add_node(
                risk_id,
                "risk",
                "Rizikový signál",
                signal=signal,
                certainty=flag.get("jistota"),
                source=flag.get("zdroj"),
                company_name=company_name,
                company_ico=company_ico,
            )
            add_edge(
                company_id,
                risk_id,
                "rizikový signál",
                "rizikový signál",
                source_url=flag.get("zdroj"),
            )

    for address, company_ids in address_usage.items():
        address_id = f"address:{address.lower()}"
        label = "sdílená adresa" if len(company_ids) > 1 else "adresa"
        for company_id in sorted(company_ids):
            add_edge(
                company_id,
                address_id,
                label,
                label,
                companies_at_address=len(company_ids),
            )
        nodes[address_id]["meta"]["shared"] = len(company_ids) > 1

    for node in nodes.values():
        meta = node["meta"]
        if "companies" in meta:
            meta["companies"] = sorted(set(meta["companies"]))
            meta["company_count"] = len(meta["companies"])
        if "company_ids" in meta:
            meta["company_ids"] = sorted(set(meta["company_ids"]))
        if "roles" in meta:
            meta["roles"] = sorted(set(meta["roles"]))
        if "relationship_states" in meta:
            meta["relationship_states"] = sorted(set(meta["relationship_states"]))

    stats = {
        "companies": sum(1 for node in nodes.values() if node["type"] == "company"),
        "people": sum(1 for node in nodes.values() if node["type"] == "person"),
        "addresses": sum(1 for node in nodes.values() if node["type"] == "address"),
        "risks": sum(1 for node in nodes.values() if node["type"] == "risk"),
        "relationships": len(edges),
    }

    return {"nodes": list(nodes.values()), "edges": edges, "stats": stats}


def filter_visual_relationship_dataset(
    graph_data: dict[str, Any],
    *,
    show_companies: bool,
    show_people: bool,
    show_addresses: bool,
    show_historical: bool,
    show_risks: bool,
    max_companies: int = 140,
    max_people: int = 320,
    max_nodes: int = 900,
) -> dict[str, Any]:
    allowed_types: set[str] = set()
    if show_companies:
        allowed_types.add("company")
    if show_people:
        allowed_types.add("person")
    if show_addresses:
        allowed_types.add("address")
    if show_risks:
        allowed_types.add("risk")

    base_nodes = {
        node["id"]: node
        for node in graph_data["nodes"]
        if node["type"] in allowed_types
    }

    filtered_edges = [
        edge
        for edge in graph_data["edges"]
        if edge["source"] in base_nodes
        and edge["target"] in base_nodes
        and (show_historical or not edge.get("historical"))
        and (show_risks or edge["type"] != "rizikový signál")
    ]

    connected_node_ids = {edge["source"] for edge in filtered_edges} | {
        edge["target"] for edge in filtered_edges
    }
    nodes = {
        node_id: node
        for node_id, node in base_nodes.items()
        if node["type"] == "company" or node_id in connected_node_ids
    }

    degree_map: dict[str, int] = {node_id: 0 for node_id in nodes}
    for edge in filtered_edges:
        if edge["source"] in degree_map:
            degree_map[edge["source"]] += 1
        if edge["target"] in degree_map:
            degree_map[edge["target"]] += 1

    hidden_nodes: dict[str, dict[str, Any]] = {}
    for node_type, limit in (("company", max_companies), ("person", max_people)):
        type_nodes = [node for node in nodes.values() if node["type"] == node_type]
        if len(type_nodes) <= limit:
            continue
        ranked = sorted(
            type_nodes,
            key=lambda item: (
                degree_map.get(item["id"], 0),
                item["label"],
            ),
            reverse=True,
        )
        keep_ids = {node["id"] for node in ranked[:limit]}
        for node in type_nodes:
            if node["id"] not in keep_ids:
                hidden_nodes[node["id"]] = node
                nodes.pop(node["id"], None)

    while len(nodes) > max_nodes:
        removable_people = [
            node for node in nodes.values() if node["type"] == "person"
        ]
        if not removable_people:
            break
        removable_people.sort(
            key=lambda item: (degree_map.get(item["id"], 0), item["label"])
        )
        node = removable_people[0]
        hidden_nodes[node["id"]] = node
        nodes.pop(node["id"], None)

    aggregate_specs = {
        "company": {
            "id": "group:company",
            "label": f"Dalších {sum(1 for node in hidden_nodes.values() if node['type'] == 'company')} firem",
            "type": "group_company",
            "meta_key": "companies",
        },
        "person": {
            "id": "group:person",
            "label": f"Dalších {sum(1 for node in hidden_nodes.values() if node['type'] == 'person')} osob",
            "type": "group_person",
            "meta_key": "people",
        },
    }

    aggregate_nodes: dict[str, dict[str, Any]] = {}
    aggregate_edges: dict[tuple[str, str, str], dict[str, Any]] = {}

    def visible_or_group(node_id: str) -> str | None:
        if node_id in nodes:
            return node_id
        hidden = hidden_nodes.get(node_id)
        if not hidden:
            return None
        group_type = hidden["type"]
        spec = aggregate_specs.get(group_type)
        if not spec:
            return None
        aggregate_node = aggregate_nodes.setdefault(
            spec["id"],
            {
                "id": spec["id"],
                "type": spec["type"],
                "label": spec["label"],
                "meta": {spec["meta_key"]: []},
            },
        )
        aggregate_node["meta"][spec["meta_key"]].append(hidden["label"])
        return spec["id"]

    for edge in filtered_edges:
        source_id = visible_or_group(edge["source"])
        target_id = visible_or_group(edge["target"])
        if not source_id or not target_id or source_id == target_id:
            continue
        edge_key = (source_id, target_id, edge["label"])
        aggregate_edge = aggregate_edges.get(edge_key)
        if not aggregate_edge:
            aggregate_edges[edge_key] = {
                **edge,
                "source": source_id,
                "target": target_id,
                "count": 1,
            }
        else:
            aggregate_edge["count"] += 1

    for aggregate_node in aggregate_nodes.values():
        for meta_key in ("companies", "people"):
            if meta_key in aggregate_node["meta"]:
                aggregate_node["meta"][meta_key] = sorted(set(aggregate_node["meta"][meta_key]))

    final_nodes = list(nodes.values()) + list(aggregate_nodes.values())
    final_edges = list(aggregate_edges.values())

    final_stats = {
        "companies": sum(1 for node in final_nodes if node["type"] == "company"),
        "people": sum(1 for node in final_nodes if node["type"] == "person"),
        "addresses": sum(1 for node in final_nodes if node["type"] == "address"),
        "risks": sum(1 for node in final_nodes if node["type"] == "risk"),
        "relationships": len(final_edges),
    }

    return {
        "nodes": final_nodes,
        "edges": final_edges,
        "stats": final_stats,
        "aggregated": {
            "companies_hidden": sum(
                1 for node in hidden_nodes.values() if node["type"] == "company"
            ),
            "people_hidden": sum(
                1 for node in hidden_nodes.values() if node["type"] == "person"
            ),
        },
    }
