"""Načítání a ukládání perzistentního stavu aplikace."""

import json
import os
from typing import Any

from core.config import APP_STATE_PATH


def _is_production_runtime() -> bool:
    return bool(os.getenv("RENDER"))


def load_persisted_state() -> dict[str, Any]:
    if _is_production_runtime():
        return {}
    if not APP_STATE_PATH.exists():
        return {}
    try:
        return json.loads(APP_STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def save_persisted_state(state: dict[str, Any]) -> None:
    if _is_production_runtime():
        return
    try:
        APP_STATE_PATH.write_text(
            json.dumps(state, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError:
        pass
