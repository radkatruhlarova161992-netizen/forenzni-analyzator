"""Načítání a ukládání perzistentního stavu aplikace."""

import json
from typing import Any

from core.config import APP_STATE_PATH


def load_persisted_state() -> dict[str, Any]:
    if not APP_STATE_PATH.exists():
        return {}
    try:
        return json.loads(APP_STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def save_persisted_state(state: dict[str, Any]) -> None:
    try:
        APP_STATE_PATH.write_text(
            json.dumps(state, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError:
        pass
