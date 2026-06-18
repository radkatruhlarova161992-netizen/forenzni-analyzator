"""Obecné pomocné funkce."""

import re
from datetime import datetime
from urllib.parse import quote

from core.config import KURZY_SEARCH_URL


def clean_ico(raw: str) -> str:
    digits = re.sub(r"\D", "", raw)
    if not digits:
        return ""
    return digits.zfill(8)


def parse_ico_list(text: str) -> list[str]:
    raw_items = re.split(r"[,\n;]+", text)
    icos: list[str] = []
    for item in raw_items:
        ico = clean_ico(item)
        if ico and ico not in icos:
            icos.append(ico)
    return icos


def parse_person_list(text: str) -> list[str]:
    raw_items = re.split(r"[\n;,]+", text)
    people: list[str] = []
    for item in raw_items:
        name = " ".join(item.strip().split())
        if name and name not in people:
            people.append(name)
    return people


def now_str() -> str:
    return datetime.now().strftime("%d.%m.%Y %H:%M")


def format_role_status(is_current: bool) -> str:
    return "Aktuální" if is_current else "Historická"


def format_kurzy_search_link(query: str, only_valid: bool) -> str:
    return KURZY_SEARCH_URL.format(query=quote(query), only_valid=str(only_valid))


def normalize_name(value: str) -> str:
    return " ".join(str(value or "").upper().split())
