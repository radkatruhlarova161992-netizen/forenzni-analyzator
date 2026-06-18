"""Diagnostika dohledani vazeb pro jedno IČO."""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.utils import clean_ico  # noqa: E402
from sources.kurzy_relationships import fetch_kurzy_relationships  # noqa: E402


def main() -> int:
    ico = clean_ico(sys.argv[1] if len(sys.argv) > 1 else "")
    if not ico:
        print("Použití: python scripts/debug_relationship_lookup.py 08264252")
        return 2

    result = fetch_kurzy_relationships(ico)
    relationships = result.get("relationships", []) or []
    with_ico = [row for row in relationships if row.get("ico")]
    without_ico = [row for row in relationships if not row.get("ico")]
    diagnostics = result.get("diagnostics") or {}

    print(f"IČO: {ico}")
    print(f"Status Kurzy: {result.get('status')}")
    print(f"URL: {result.get('source_url')}")
    print(f"Celkem vazeb: {len(relationships)}")
    print(f"S IČO: {len(with_ico)}")
    print(f"Bez IČO: {len(without_ico)}")
    print(f"Vynechané duplicity: {diagnostics.get('kurzy_skipped_duplicates', 0)}")
    if result.get("error"):
        print(f"Chyba: {result.get('error')}")
    for warning in diagnostics.get("parser_warnings") or []:
        print(f"Varování parseru: {warning}")

    print("\nPrvních 30 vazeb:")
    for index, row in enumerate(relationships[:30], start=1):
        print(
            f"{index}. {row.get('firma') or row.get('nazev')} | "
            f"IČO: {row.get('ico') or '-'} | "
            f"Typ: {row.get('typ_vazby') or row.get('role')} | "
            f"Ověření: {row.get('verification_label') or row.get('verification_status')}"
        )

    output_dir = ROOT_DIR / "data"
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / f"debug_{ico}.json"
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nUloženo: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
