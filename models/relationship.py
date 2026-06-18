"""Dataclass vztahu mezi subjekty."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class Relationship:
    subjekt_od: str
    subjekt_do: str
    typ: str
    role: str | None = None
    od: str | None = None
    do: str | None = None
    stav_vazby: str | None = None
    zdroj: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
