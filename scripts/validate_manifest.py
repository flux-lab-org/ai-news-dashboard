#!/usr/bin/env python3
"""Verify the committed archive manifest matches the report source files.

The builder's ``generated_at`` value is intentionally ignored because it is the
only nondeterministic field. This check never writes or repairs the manifest.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "html" / "archive" / "manifest.json"

sys.path.insert(0, str(ROOT / "scripts"))
from build_manifest import build_manifest  # type: ignore  # noqa: E402


def _display(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _without_timestamp(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _without_timestamp(v) for k, v in value.items() if k != "generated_at"}
    if isinstance(value, list):
        return [_without_timestamp(v) for v in value]
    return value


def validate_manifest(path: Path = OUT) -> list[str]:
    errors: list[str] = []
    if not path.is_file():
        return [f"{_display(path)}: committed manifest is missing"]

    try:
        committed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        return [f"{_display(path)}: malformed JSON: {e}"]

    if not isinstance(committed, dict):
        return [f"{_display(path)}: manifest root must be an object"]
    if not isinstance(committed.get("generated_at"), str):
        errors.append(f"{_display(path)}: generated_at must be a string")

    try:
        expected = build_manifest()
    except (OSError, ValueError, TypeError) as e:
        return [f"source reports could not produce a manifest: {e}"]

    if _without_timestamp(committed) != _without_timestamp(expected):
        errors.append(
            f"{_display(path)}: committed content is stale or inconsistent "
            "with archive REPORT data; run build_manifest.py and commit the result"
        )
    return errors


def main() -> int:
    errors = validate_manifest()
    if errors:
        print("Manifest validation failed:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1
    print(f"Manifest is current: {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
