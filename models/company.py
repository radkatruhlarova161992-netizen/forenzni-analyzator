"""Dataclass firmy."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class Company:
    ico: str
    nazev: str | None = None
    sidlo: str | None = None
    pravni_forma: str | None = None
    stav: str | None = None
    v_likvidaci: bool = False
    datum_vzniku: str | None = None
    datum_zaniku: str | None = None
    zdroje: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
