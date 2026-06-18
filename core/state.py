"""Souborová persistence je vypnutá; stav žije jen v session state."""

from typing import Any


def load_persisted_state() -> dict[str, Any]:
    return {}


def save_persisted_state(state: dict[str, Any]) -> None:
    _ = state
