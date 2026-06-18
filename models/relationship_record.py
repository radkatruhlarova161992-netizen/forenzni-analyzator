"""Jednotny datovy objekt pro vztahy mezi subjekty."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


VerificationStatus = Literal[
    "verified_primary",
    "verified_secondary",
    "unverified_external",
    "candidate_match",
    "failed_lookup",
]


@dataclass(slots=True)
class RelationshipRecord:
    source_entity_name: str | None
    source_ico: str | None
    target_entity_name: str
    target_ico: str | None = None
    target_address: str | None = None
    target_type: str = "unknown"
    relationship_type: str = "vazba"
    relationship_direction: str = "undirected"
    valid_from: str | None = None
    valid_to: str | None = None
    is_historical: bool = False
    is_current: bool = True
    source_name: str = ""
    source_url: str | None = None
    confidence: str = "medium"
    verification_status: VerificationStatus = "unverified_external"
    raw_evidence: str | None = None
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_legacy_dict(self) -> dict[str, Any]:
        """Prevede zaznam na strukturu, kterou uz umi zbytek aplikace zobrazit."""
        return {
            "nazev": self.target_entity_name,
            "firma": self.target_entity_name,
            "jmeno": self.target_entity_name,
            "ico": self.target_ico,
            "adresa": self.target_address,
            "typ_vazby": self.relationship_type,
            "role": self.relationship_type,
            "od": self.valid_from,
            "do": self.valid_to,
            "stav_vazby": "Historická" if self.is_historical else "Aktuální",
            "source_name": self.source_name,
            "source_url": self.source_url,
            "confidence": self.confidence,
            "verification_status": self.verification_status,
            "verification_label": verification_label(self.verification_status),
            "raw_evidence": self.raw_evidence,
            "warnings": self.warnings,
            "zdroj_cast": self.source_name,
            "entity_type": self.target_type,
            "kurzy_vazby_link": self.source_url,
        }


def verification_label(status: str | None) -> str:
    labels = {
        "verified_primary": "ověřeno primárním zdrojem",
        "verified_secondary": "ověřeno sekundárním zdrojem",
        "unverified_external": "nutno ověřit",
        "candidate_match": "kandidát k ověření",
        "failed_lookup": "nepodařilo se ověřit",
    }
    return labels.get(str(status or ""), "nutno ověřit")
