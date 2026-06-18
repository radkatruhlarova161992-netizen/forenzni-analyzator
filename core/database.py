"""Databazova vrstva pro lokalni sklad Connexa."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
import json
import sqlite3
from typing import Any, Iterator

from core.config import CACHE_MAX_AGE_DAYS, DATABASE_PATH


def now_utc_iso() -> str:
    return datetime.now(UTC).isoformat()


def parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def initialize_database() -> None:
    with get_connection() as connection:
        connection.executescript(
            """
            PRAGMA foreign_keys = OFF;

            CREATE TABLE IF NOT EXISTS companies (
                ico TEXT PRIMARY KEY,
                nazev TEXT,
                pravni_forma TEXT,
                stav TEXT,
                datum_vzniku TEXT,
                adresa TEXT,
                posledni_aktualizace TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS persons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                jmeno TEXT NOT NULL,
                funkce TEXT,
                UNIQUE(jmeno, funkce)
            );

            CREATE TABLE IF NOT EXISTS addresses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                adresa TEXT NOT NULL UNIQUE
            );

            CREATE TABLE IF NOT EXISTS relationships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id TEXT NOT NULL,
                source_type TEXT NOT NULL,
                target_id TEXT NOT NULL,
                target_type TEXT NOT NULL,
                typ_vazby TEXT NOT NULL,
                role TEXT,
                od TEXT,
                do TEXT,
                historicka INTEGER NOT NULL DEFAULT 0,
                zdroj TEXT
            );

            CREATE TABLE IF NOT EXISTS risks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subjekt TEXT NOT NULL,
                typ_rizika TEXT NOT NULL,
                zdroj TEXT,
                datum TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS company_cache (
                ico TEXT NOT NULL,
                include_historical INTEGER NOT NULL DEFAULT 0,
                payload_json TEXT NOT NULL,
                posledni_aktualizace TEXT NOT NULL,
                PRIMARY KEY (ico, include_historical)
            );

            CREATE TABLE IF NOT EXISTS company_cache_v2 (
                ico TEXT NOT NULL,
                include_historical INTEGER NOT NULL DEFAULT 0,
                include_public_aggregators INTEGER NOT NULL DEFAULT 0,
                payload_json TEXT NOT NULL,
                posledni_aktualizace TEXT NOT NULL,
                PRIMARY KEY (ico, include_historical, include_public_aggregators)
            );

            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_relationships_source
            ON relationships(source_id, source_type);

            CREATE INDEX IF NOT EXISTS idx_relationships_target
            ON relationships(target_id, target_type);

            CREATE UNIQUE INDEX IF NOT EXISTS idx_relationships_unique
            ON relationships(source_id, target_id, typ_vazby, role, od, do, historicka);

            CREATE INDEX IF NOT EXISTS idx_risks_subjekt
            ON risks(subjekt);
            """
        )


def load_cached_source_data(
    ico: str,
    include_historical: bool,
    include_public_aggregators: bool = False,
    max_age_days: int = CACHE_MAX_AGE_DAYS,
) -> dict[str, Any] | None:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT payload_json, posledni_aktualizace
            FROM company_cache_v2
            WHERE ico = ? AND include_historical = ? AND include_public_aggregators = ?
            """,
            (ico, int(include_historical), int(include_public_aggregators)),
        ).fetchone()

    if not row:
        return None

    updated_at = parse_iso_datetime(row["posledni_aktualizace"])
    if not updated_at:
        return None
    if datetime.now(UTC) - updated_at > timedelta(days=max_age_days):
        return None

    try:
        return json.loads(row["payload_json"])
    except json.JSONDecodeError:
        return None


def save_cached_source_data(
    ico: str,
    include_historical: bool,
    include_public_aggregators: bool,
    payload: dict[str, Any],
) -> None:
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO company_cache_v2 (
                ico, include_historical, include_public_aggregators, payload_json, posledni_aktualizace
            )
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(ico, include_historical, include_public_aggregators) DO UPDATE SET
                payload_json = excluded.payload_json,
                posledni_aktualizace = excluded.posledni_aktualizace
            """,
            (
                ico,
                int(include_historical),
                int(include_public_aggregators),
                json.dumps(payload, ensure_ascii=False),
                now_utc_iso(),
            ),
        )


def _upsert_company(
    connection: sqlite3.Connection,
    ico: str,
    nazev: str | None,
    pravni_forma: str | None,
    stav: str | None,
    datum_vzniku: str | None,
    adresa: str | None,
    updated_at: str,
) -> None:
    connection.execute(
        """
        INSERT INTO companies (ico, nazev, pravni_forma, stav, datum_vzniku, adresa, posledni_aktualizace)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(ico) DO UPDATE SET
            nazev = COALESCE(excluded.nazev, companies.nazev),
            pravni_forma = COALESCE(excluded.pravni_forma, companies.pravni_forma),
            stav = COALESCE(excluded.stav, companies.stav),
            datum_vzniku = COALESCE(excluded.datum_vzniku, companies.datum_vzniku),
            adresa = COALESCE(excluded.adresa, companies.adresa),
            posledni_aktualizace = excluded.posledni_aktualizace
        """,
        (ico, nazev, pravni_forma, stav, datum_vzniku, adresa, updated_at),
    )


def _get_or_create_person(
    connection: sqlite3.Connection,
    jmeno: str,
    funkce: str | None,
) -> int:
    row = connection.execute(
        "SELECT id FROM persons WHERE jmeno = ? AND funkce IS ?",
        (jmeno, funkce),
    ).fetchone()
    if row:
        return int(row["id"])

    cursor = connection.execute(
        "INSERT INTO persons (jmeno, funkce) VALUES (?, ?)",
        (jmeno, funkce),
    )
    return int(cursor.lastrowid)


def _get_or_create_address(connection: sqlite3.Connection, adresa: str) -> int:
    row = connection.execute(
        "SELECT id FROM addresses WHERE adresa = ?",
        (adresa,),
    ).fetchone()
    if row:
        return int(row["id"])

    cursor = connection.execute(
        "INSERT INTO addresses (adresa) VALUES (?)",
        (adresa,),
    )
    return int(cursor.lastrowid)


def save_company_record(record: dict[str, Any]) -> None:
    ico = str(record.get("ico") or "")
    if not ico:
        return

    updated_at = now_utc_iso()
    company_source_id = f"company:{ico}"
    company_address = record.get("sidlo_raw") or record.get("sidlo")

    with get_connection() as connection:
        _upsert_company(
            connection,
            ico=ico,
            nazev=record.get("nazev"),
            pravni_forma=record.get("pravni_forma"),
            stav=record.get("stav"),
            datum_vzniku=record.get("datum_vzniku"),
            adresa=company_address,
            updated_at=updated_at,
        )

        connection.execute("DELETE FROM relationships WHERE source_id = ?", (company_source_id,))
        connection.execute("DELETE FROM risks WHERE subjekt = ?", (ico,))

        if company_address:
            address_id = _get_or_create_address(connection, company_address)
            connection.execute(
                """
                INSERT OR REPLACE INTO relationships (
                    source_id, source_type, target_id, target_type, typ_vazby, role, od, do, historicka, zdroj
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    company_source_id,
                    "company",
                    f"address:{address_id}",
                    "address",
                    "sídlo",
                    "Sídlo společnosti",
                    "",
                    "",
                    0,
                    record.get("zdroj_ares") or "",
                ),
            )

        for person in record.get("osoby", []) or []:
            person_name = str(person.get("jmeno") or "").strip()
            if not person_name:
                continue
            person_role = person.get("role")
            person_id = _get_or_create_person(connection, person_name, person_role)
            connection.execute(
                """
                INSERT OR REPLACE INTO relationships (
                    source_id, source_type, target_id, target_type, typ_vazby, role, od, do, historicka, zdroj
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    company_source_id,
                    "company",
                    f"person:{person_id}",
                    "person",
                    person_role or "osoba",
                    person_role or "",
                    person.get("od") or "",
                    person.get("do") or "",
                    int(str(person.get("stav_vazby") or "").lower().startswith("histor")),
                    person.get("kurzy_vazby_link") or person.get("zdroj_url") or "",
                ),
            )

            person_address = str(person.get("adresa") or "").strip()
            if person_address:
                address_id = _get_or_create_address(connection, person_address)
                connection.execute(
                    """
                    INSERT OR REPLACE INTO relationships (
                        source_id, source_type, target_id, target_type, typ_vazby, role, od, do, historicka, zdroj
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        f"person:{person_id}",
                        "person",
                        f"address:{address_id}",
                        "address",
                        "adresa",
                        "Adresa osoby",
                        "",
                        "",
                        0,
                        person.get("kurzy_vazby_link") or person.get("zdroj_url") or "",
                    ),
                )

        for linked_company in record.get("navazane_firmy", []) or []:
            linked_ico = str(linked_company.get("ico") or "").strip()
            linked_name = linked_company.get("firma")
            if not linked_ico and not linked_name:
                continue
            if linked_ico:
                _upsert_company(
                    connection,
                    ico=linked_ico,
                    nazev=linked_name,
                    pravni_forma=None,
                    stav=None,
                    datum_vzniku=None,
                    adresa=None,
                    updated_at=updated_at,
                )
                target_id = f"company:{linked_ico}"
            else:
                target_id = f"external_company:{linked_name}"

            connection.execute(
                """
                INSERT OR REPLACE INTO relationships (
                    source_id, source_type, target_id, target_type, typ_vazby, role, od, do, historicka, zdroj
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    company_source_id,
                    "company",
                    target_id,
                    "company",
                    linked_company.get("role") or "navázaná firma",
                    linked_company.get("role") or "",
                    linked_company.get("od") or "",
                    linked_company.get("do") or "",
                    int(
                        str(linked_company.get("stav_vazby") or "").lower().startswith(
                            "histor"
                        )
                    ),
                    linked_company.get("kurzy_vazby_link") or linked_company.get("zdroj_url") or "",
                ),
            )

        for flag in record.get("risk_flags", []) or []:
            connection.execute(
                """
                INSERT INTO risks (subjekt, typ_rizika, zdroj, datum)
                VALUES (?, ?, ?, ?)
                """,
                (
                    ico,
                    flag.get("signal"),
                    flag.get("zdroj"),
                    updated_at,
                ),
            )


def list_cached_subjects() -> list[tuple[str, bool, bool]]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT ico, include_historical, include_public_aggregators
            FROM company_cache_v2
            ORDER BY ico, include_public_aggregators
            """
        ).fetchall()
    return [
        (
            str(row["ico"]),
            bool(row["include_historical"]),
            bool(row["include_public_aggregators"]),
        )
        for row in rows
    ]


def get_metadata(key: str) -> str | None:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT value FROM metadata WHERE key = ?",
            (key,),
        ).fetchone()
    return str(row["value"]) if row else None


def set_metadata(key: str, value: str) -> None:
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO metadata (key, value)
            VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, value),
        )
