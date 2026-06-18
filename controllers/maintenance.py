"""Udrzba lokalni cache databaze."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from analysis.entities import fetch_company_data, normalize_entities
from analysis.risk import calculate_risk_signals
from core.config import WEEKLY_REFRESH_INTERVAL_DAYS
from core.database import (
    get_metadata,
    list_cached_subjects,
    now_utc_iso,
    parse_iso_datetime,
    save_cached_source_data,
    save_company_record,
    set_metadata,
)

WEEKLY_REFRESH_METADATA_KEY = "last_weekly_refresh"


def refresh_cached_subjects_if_due() -> None:
    last_run = parse_iso_datetime(get_metadata(WEEKLY_REFRESH_METADATA_KEY))
    if last_run and datetime.now(UTC) - last_run < timedelta(days=WEEKLY_REFRESH_INTERVAL_DAYS):
        return

    for ico, include_historical in list_cached_subjects():
        try:
            source_data = fetch_company_data(
                ico,
                include_historical=include_historical,
                force_refresh=True,
            )
            save_cached_source_data(ico, include_historical, source_data)
            record = calculate_risk_signals(normalize_entities(source_data))
            save_company_record(record)
        except Exception:
            continue

    set_metadata(WEEKLY_REFRESH_METADATA_KEY, now_utc_iso())
