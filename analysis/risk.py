"""Vyhodnocení neutrálních rizikových signálů."""

from typing import Any


def evaluate_risk_flags(record: dict[str, Any]) -> list[dict[str, str | None]]:
    flags: list[dict[str, str | None]] = []

    if record.get("v_likvidaci"):
        flags.append(
            {
                "signal": "Společnost je v likvidaci",
                "jistota": "ověřené (ARES)",
                "zdroj": record.get("zdroj_ares"),
            }
        )

    if record.get("nespolehlivy_platce") is True:
        flags.append(
            {
                "signal": "Společnost je evidována jako nespolehlivý plátce DPH",
                "jistota": "ověřené (registr DPH)",
                "zdroj": record.get("zdroj_dph"),
            }
        )

    if record.get("datum_zaniku"):
        flags.append(
            {
                "signal": f"Subjekt má evidováno datum zániku ({record.get('datum_zaniku')})",
                "jistota": "ověřené (ARES)",
                "zdroj": record.get("zdroj_ares"),
            }
        )

    if record.get("isir_status") in ("vyzaduje_rucni_kontrolu", "castecny_vysledek"):
        flags.append(
            {
                "signal": "Insolvenční rejstřík nelze automaticky vyhodnotit – nutná ruční kontrola",
                "jistota": "neověřené – vyžaduje ruční kontrolu",
                "zdroj": record.get("link_isir"),
            }
        )

    if record.get("sbirka_status") in ("failed", "error", "nenalezeno", "timeout"):
        flags.append(
            {
                "signal": "Sbírku listin nelze automaticky ověřit (chybějící účetní závěrky 2023–2025 nutno zkontrolovat ručně)",
                "jistota": "neověřené – vyžaduje ruční kontrolu",
                "zdroj": record.get("link_sbirka_listin"),
            }
        )

    return flags


def compute_risk_level(flags: list[dict[str, str | None]]) -> str:
    overene = [flag for flag in flags if str(flag.get("jistota", "")).startswith("ověřené")]
    if len(overene) >= 2:
        return "Vysoké"
    if len(overene) == 1:
        return "Zvýšené"
    if flags:
        return "Střední (nutno ověřit)"
    return "Nízké"


def calculate_risk_signals(record: dict[str, Any]) -> dict[str, Any]:
    """Dopočítá rizikové signály nad normalizovaným záznamem."""
    flags = evaluate_risk_flags(record)
    return {
        **record,
        "risk_flags": flags,
        "risk_level": compute_risk_level(flags),
    }
