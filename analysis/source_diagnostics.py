"""Souhrn stavu zdroju a vazeb pro UI diagnostiku."""

from __future__ import annotations

from typing import Any


PRIMARY_VERIFICATION_STATUSES = {"verified_primary", "verified_secondary"}
EXTERNAL_VERIFICATION_STATUSES = {"unverified_external", "candidate_match"}


def classify_relationship_source(item: dict[str, Any]) -> str:
    status = str(item.get("verification_status") or "")
    source_name = str(item.get("source_name") or item.get("zdroj_cast") or "")
    if status in PRIMARY_VERIFICATION_STATUSES:
        return "verified"
    if status in EXTERNAL_VERIFICATION_STATUSES or "Kurzy" in source_name:
        return "external"
    return "verified"


def build_source_diagnostics(
    record: dict[str, Any],
    source_data: dict[str, Any] | None = None,
    merged_skipped: int = 0,
) -> dict[str, Any]:
    relationships = record.get("navazane_firmy", []) or []
    people = record.get("osoby", []) or []
    source_data = source_data or {}
    kurzy_data = source_data.get("kurzy_relationships") or {}
    kurzy_diagnostics = kurzy_data.get("diagnostics") or {}

    verified = [
        item
        for item in relationships
        if classify_relationship_source(item) == "verified"
    ]
    external = [
        item
        for item in relationships
        if classify_relationship_source(item) == "external"
    ]
    pending_ico = [item for item in external if not item.get("ico")]
    candidates = [
        item
        for item in relationships
        if item.get("verification_status") == "candidate_match"
    ]

    statuses = {
        "ARES": record.get("ares_status") or "načteno",
        "Justice": "načteno"
        if record.get("osoby") or record.get("navazane_firmy")
        else "bez vazeb v načtených datech",
        "Kurzy.cz": kurzy_data.get("status") or "vypnuto",
        "ISIR": record.get("isir_status") or "načteno",
        "ADIS": record.get("dph_status") or "načteno",
        "Cache": "načteno",
    }

    source_errors = {
        "ARES": record.get("ares_chyba"),
        "Kurzy.cz": kurzy_data.get("error"),
        "ISIR": record.get("isir_chyba"),
        "ADIS": record.get("dph_chyba"),
    }
    source_errors = {key: value for key, value in source_errors.items() if value}

    return {
        "statuses": statuses,
        "counts": {
            "verified_relationships": len(verified) + len(people),
            "unverified_external_relationships": len(external),
            "pending_ico_relationships": len(pending_ico),
            "candidate_relationships": len(candidates),
            "skipped_relationships": merged_skipped,
            "source_errors": len(source_errors),
            "kurzy_raw": int(kurzy_diagnostics.get("kurzy_total_raw") or 0),
            "kurzy_deduped": int(kurzy_diagnostics.get("kurzy_total_deduped") or 0),
            "kurzy_without_ico": int(kurzy_diagnostics.get("kurzy_without_ico") or 0),
        },
        "errors": source_errors,
        "parser_warnings": kurzy_diagnostics.get("parser_warnings") or kurzy_data.get("warnings") or [],
    }


def build_external_gap_warning(record: dict[str, Any]) -> str | None:
    diagnostics = record.get("source_diagnostics") or {}
    counts = diagnostics.get("counts") or {}
    kurzy_total = int(counts.get("kurzy_deduped") or record.get("relationship_diagnostics", {}).get("kurzy") or 0)
    verified = int(counts.get("verified_relationships") or record.get("verified_relationship_count") or 0)
    pending_ico = int(counts.get("pending_ico_relationships") or 0)

    if kurzy_total <= verified + 5 or kurzy_total <= verified:
        return None

    detail = (
        f"Z Kurzy.cz bylo nalezeno {kurzy_total} možných vazeb, "
        f"ale pouze {verified} bylo plně ověřeno přes primární zdroje."
    )
    if pending_ico:
        detail += f" {pending_ico} vazeb čeká na doplnění IČO."
    return detail


def summarize_case_diagnostics(results: list[dict[str, Any]]) -> dict[str, int]:
    totals = {
        "verified_relationships": 0,
        "unverified_external_relationships": 0,
        "pending_ico_relationships": 0,
        "source_errors": 0,
    }
    for record in results:
        counts = (record.get("source_diagnostics") or {}).get("counts") or {}
        for key in totals:
            totals[key] += int(counts.get(key) or 0)
    return totals
