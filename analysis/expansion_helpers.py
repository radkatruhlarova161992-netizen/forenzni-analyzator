"""Expanze sítě přes osoby a adresy."""

from __future__ import annotations

from typing import Any

from sources.company_search import search_company_candidates
from core.utils import normalize_name


def expand_by_person(
    person_name: str,
    person_role: str | None = None,
    person_birth_date: str | None = None,
) -> list[dict[str, Any]]:
    """
    Rozšíří síť hledáním dalších firem, kde se osoba objevuje.
    
    Vrací:
    {
        "ico": "...",
        "name": "...",
        "confidence": "high" | "medium" | "low",
        "source_name": "...",
        "source_url": "...",
        "verification_status": "...",
        "warning": "..."  (pokud nemá narození, confidence = low + warning)
    }
    """
    if not person_name or len(person_name) < 3:
        return []

    results: list[dict[str, Any]] = []
    candidates = search_company_candidates(person_name)

    confidence_base = "high" if person_birth_date else "medium"
    warning = None
    if not person_birth_date:
        warning = f"Osoba {person_name} nemá zadáno datum narození - výsledky mohou obsahovat falešné shody."
        confidence_base = "low"

    for candidate in candidates:
        ico = candidate.get("ico")
        if ico:
            results.append({
                "ico": ico,
                "name": candidate.get("nazev"),
                "confidence": confidence_base,
                "source_name": candidate.get("source_name"),
                "source_url": candidate.get("source_url"),
                "verification_status": "candidate_needs_verification",
                "warning": warning,
                "search_person_name": person_name,
                "search_person_role": person_role,
            })

    return results


def expand_by_address(
    address: str,
    address_type: str = "current",
) -> list[dict[str, Any]]:
    """
    Rozšíří síť hledáním dalších firem na stejné adrese.
    
    Vrací:
    {
        "ico": "...",
        "name": "...",
        "confidence": "high",
        "verification_status": "verified_primary",
        "address_type": "same_current_address" | "same_historical_address",
    }
    
    TODO: Implementovat skutečné hledání v ARES/Justice podle adresy.
    Zatím vrací prázdný seznam.
    """
    if not address or len(address) < 8:
        return []

    # TODO: Implementovat API pro hledání firem podle adresy
    # Například:
    # - ARES VR má API pro vyhledávání podle adresy
    # - Justice.cz má rejstřík adres
    # - Kurzy.cz má vyhledávání podle sídla
    
    return []


def resolve_candidate_company(
    company_name: str,
    address: str | None = None,
) -> dict[str, Any] | None:
    """
    Pokusí se vyřešit kandidátní firmu na konkrétní IČO.
    
    Vrací:
    {
        "ico": "...",
        "name": "...",
        "confidence": "high" | "medium" | "low",
        "source_name": "...",
        "source_url": "...",
        "verification_status": "resolved" | "candidate_needs_manual_verification",
    }
    
    nebo None, pokud se nepodařilo vyřešit.
    """
    if not company_name or len(company_name) < 3:
        return None

    candidates = search_company_candidates(company_name)

    if not candidates:
        return None

    # Pokud máme adresu, preferuj kandidáty s vyšší shodou adresy
    best_match = None
    best_score = 0

    for candidate in candidates:
        score = 1.0  # Základní skóre

        # Pokud má IČO, zvýš skóre
        if candidate.get("ico"):
            score += 1.0

        # Pokud se jméno přesně shoduje, zvýš skóre
        if normalize_name(candidate.get("nazev") or "") == normalize_name(company_name):
            score += 2.0

        # Pokud se adresa shoduje, zvýš skóre
        if address and candidate.get("sidlo"):
            if normalize_name(candidate.get("sidlo") or "") == normalize_name(address):
                score += 1.5

        if score > best_score:
            best_score = score
            best_match = candidate

    if not best_match:
        return None

    confidence = "high" if best_score >= 3.0 else ("medium" if best_score >= 1.5 else "low")
    verification_status = "resolved" if confidence == "high" else "candidate_needs_manual_verification"

    return {
        "ico": best_match.get("ico"),
        "name": best_match.get("nazev"),
        "confidence": confidence,
        "source_name": best_match.get("source_name"),
        "source_url": best_match.get("source_url"),
        "verification_status": verification_status,
        "original_name": company_name,
        "original_address": address,
    }
