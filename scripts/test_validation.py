#!/usr/bin/env python3
"""Focused regression tests for report and committed-manifest gates."""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_manifest import build_manifest  # type: ignore  # noqa: E402
from validate_manifest import validate_manifest  # type: ignore  # noqa: E402
from validate_report import validate_report  # type: ignore  # noqa: E402


def valid_spotlight(number: int) -> dict[str, object]:
    return {
        "title": f"Spotlight {number}",
        "tag": "enterprise",
        "bullets": ["A useful, visible finding."],
        "sourceUrl": "https://example.com/source",
        "sourceLabel": "Example",
    }


class ValidationTests(unittest.TestCase):
    def temporary_directory(self):
        scratch = Path(os.environ.get("PAPERCLIP_RUN_SCRATCH_DIR", ROOT / ".paperclip-runtime"))
        scratch.mkdir(parents=True, exist_ok=True)
        return tempfile.TemporaryDirectory(dir=scratch)

    def test_clean_report_passes(self) -> None:
        report = {"date": "2026-11-08", "spotlights": [valid_spotlight(1)]}
        self.assertEqual(validate_report(report, "fixture"), [])

    def test_fifth_spotlight_fails(self) -> None:
        report = {"date": "2026-11-08", "spotlights": [valid_spotlight(i) for i in range(5)]}
        errors = validate_report(report, "fixture")
        self.assertTrue(any("cap is 4" in error for error in errors))

    def test_missing_manifest_fails(self) -> None:
        with self.temporary_directory() as directory:
            errors = validate_manifest(Path(directory) / "manifest.json")
        self.assertTrue(any("missing" in error for error in errors))

    def test_malformed_manifest_fails(self) -> None:
        with self.temporary_directory() as directory:
            path = Path(directory) / "manifest.json"
            path.write_text("{not json", encoding="utf-8")
            errors = validate_manifest(path)
        self.assertTrue(any("malformed JSON" in error for error in errors))

    def test_stale_manifest_fails(self) -> None:
        with self.temporary_directory() as directory:
            path = Path(directory) / "manifest.json"
            manifest = build_manifest()
            manifest["count"] = manifest["count"] + 1
            path.write_text(json.dumps(manifest), encoding="utf-8")
            errors = validate_manifest(path)
        self.assertTrue(any("stale or inconsistent" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
