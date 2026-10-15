#!/usr/bin/env python3
"""
Validate the REPORT object embedded in every dashboard HTML page.

Enforces a contract between the daily content generator and the page
template so the schema-drift class of bug (template renders nothing
because data shape changed) cannot ship.

Run:
    python scripts/validate_report.py                  # validates all pages
    python scripts/validate_report.py html/index.html  # validates one file

Exits non-zero on any violation and prints a list of failures.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
HTML_DIR = ROOT / "html"
ARCHIVE_DIR = HTML_DIR / "archive"

# Reuse the JS-to-JSON converter from the manifest builder.
sys.path.insert(0, str(ROOT / "scripts"))
from build_manifest import js_object_to_json, REPORT_RE  # type: ignore

ALLOWED_TAGS = {"groove", "harmony", "both", "enterprise", "bonus"}
COMPLIANCE_SEGMENTS = {"small", "mid", "large", "all"}
COMPLIANCE_KINDS = {"in-window", "in-effect", "upcoming-deadline"}
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _fail(errors: list[str], where: str, msg: str) -> None:
    errors.append(f"{where}: {msg}")


def validate_report(report: Any, where: str) -> list[str]:
    errors: list[str] = []
    if not isinstance(report, dict):
        _fail(errors, where, "REPORT is not an object")
        return errors

    date = report.get("date")
    if not isinstance(date, str) or not DATE_RE.match(date):
        _fail(errors, where, f"REPORT.date missing or not YYYY-MM-DD: {date!r}")

    spotlights = report.get("spotlights")
    if not isinstance(spotlights, list) or not spotlights:
        _fail(errors, where, "REPORT.spotlights must be a non-empty array")
        spotlights = []

    for i, s in enumerate(spotlights):
        loc = f"{where} spotlights[{i}]"
        if not isinstance(s, dict):
            _fail(errors, loc, "not an object")
            continue
        # Heading: accept either 'title' (current) or 'headline' (legacy).
        heading = s.get("title") or s.get("headline")
        if not isinstance(heading, str) or not heading.strip():
            _fail(errors, loc, "missing 'title' (or legacy 'headline') string")
        tag = s.get("tag")
        if tag not in ALLOWED_TAGS:
            _fail(errors, loc, f"tag must be one of {sorted(ALLOWED_TAGS)}, got {tag!r}")
        # Body: accept 'bullets' (current) OR 'summary' (legacy).  At least one
        # must produce visible text on the card.
        bullets = s.get("bullets")
        summary = s.get("summary")
        has_bullets = isinstance(bullets, list) and bullets and all(
            isinstance(b, str) and b.strip() for b in bullets
        )
        has_summary = isinstance(summary, str) and summary.strip()
        if not has_bullets and not has_summary:
            _fail(errors, loc, "need non-empty 'bullets' array or 'summary' string")
        if not isinstance(s.get("sourceUrl"), str) or not s["sourceUrl"].startswith(("http://", "https://")):
            _fail(errors, loc, "missing/invalid 'sourceUrl' (must be http(s)://...)")
        if not isinstance(s.get("sourceLabel"), str) or not s["sourceLabel"].strip():
            _fail(errors, loc, "missing 'sourceLabel'")

    stories = report.get("stories")
    if stories is None:
        stories = []
    if not isinstance(stories, list):
        _fail(errors, where, "REPORT.stories must be an array (or omitted)")
        stories = []

    energy = report.get("energy")
    if energy is None:
        energy = []
    if not isinstance(energy, list):
        _fail(errors, where, "REPORT.energy must be an array (or omitted)")
        energy = []

    for i, s in [(i, s) for i, s in enumerate(stories)] + [(-1 - i, s) for i, s in enumerate(energy)]:
        loc = f"{where} stories[{i}]" if i >= 0 else f"{where} energy[{-1 - i}]"
        if not isinstance(s, dict):
            _fail(errors, loc, "not an object")
            continue
        if not isinstance(s.get("title"), str) or not s["title"].strip():
            _fail(errors, loc, "missing 'title' string")
        tag = s.get("tag")
        if tag not in ALLOWED_TAGS:
            _fail(errors, loc, f"tag must be one of {sorted(ALLOWED_TAGS)}, got {tag!r}")
        if not isinstance(s.get("sourceUrl"), str) or not s["sourceUrl"].startswith(("http://", "https://")):
            _fail(errors, loc, "missing/invalid 'sourceUrl'")
        if not isinstance(s.get("sourceLabel"), str) or not s["sourceLabel"].strip():
            _fail(errors, loc, "missing 'sourceLabel'")

    compliance = report.get("compliance")
    if compliance is None:
        compliance = []
    if not isinstance(compliance, list):
        _fail(errors, where, "REPORT.compliance must be an array (or omitted)")
        compliance = []
    for i, c in enumerate(compliance):
        loc = f"{where} compliance[{i}]"
        if not isinstance(c, dict):
            _fail(errors, loc, "not an object")
            continue
        if not isinstance(c.get("title"), str) or not c["title"].strip():
            _fail(errors, loc, "missing 'title' string")
        if c.get("tag") not in ALLOWED_TAGS:
            _fail(errors, loc, f"tag must be one of {sorted(ALLOWED_TAGS)}, got {c.get('tag')!r}")
        if c.get("segment") not in COMPLIANCE_SEGMENTS:
            _fail(errors, loc, f"segment must be one of {sorted(COMPLIANCE_SEGMENTS)}, got {c.get('segment')!r}")
        if not isinstance(c.get("region"), str) or not c["region"].strip():
            _fail(errors, loc, "missing 'region' string")
        if "kind" in c and c["kind"] not in COMPLIANCE_KINDS:
            _fail(errors, loc, f"kind must be one of {sorted(COMPLIANCE_KINDS)}, got {c['kind']!r}")
        if not isinstance(c.get("sourceUrl"), str) or not c["sourceUrl"].startswith(("http://", "https://")):
            _fail(errors, loc, "missing/invalid 'sourceUrl'")
        if not isinstance(c.get("sourceLabel"), str) or not c["sourceLabel"].strip():
            _fail(errors, loc, "missing 'sourceLabel'")
    if len(compliance) > 20:
        _fail(errors, where, f"too many compliance items ({len(compliance)}); cap is 20")

    # Counts: must have at least one spotlight (we already checked) and not exceed 8 total
    # to catch runaway generators.  README cap is 4 spotlights; we leave headroom for stories.
    if len(spotlights) > 8:
        _fail(errors, where, f"too many spotlights ({len(spotlights)}); cap is 8")
    if len(stories) > 30:
        _fail(errors, where, f"too many stories ({len(stories)}); cap is 30")
    if len(energy) > 15:
        _fail(errors, where, f"too many energy items ({len(energy)}); cap is 15")

    return errors


def _display(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def validate_file(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    m = REPORT_RE.search(text)
    if not m:
        return [f"{_display(path)}: no REPORT object found (renderer present?)"]
    try:
        report = json.loads(js_object_to_json(m.group(1)))
    except json.JSONDecodeError as e:
        return [f"{_display(path)}: REPORT not parseable as JSON: {e}"]
    return validate_report(report, _display(path))


def main(argv: list[str]) -> int:
    if len(argv) > 1:
        targets = [Path(p) for p in argv[1:]]
    else:
        targets = [HTML_DIR / "index.html"]
        for f in sorted(ARCHIVE_DIR.glob("*.html")):
            if re.match(r"^\d{4}-\d{2}-\d{2}\.html$", f.name):
                targets.append(f)

    all_errors: list[str] = []
    for t in targets:
        errs = validate_file(t)
        if errs:
            all_errors.extend(errs)
        else:
            print(f"  ok  {_display(t)}")

    if all_errors:
        print("\nValidation failed:", file=sys.stderr)
        for e in all_errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    print(f"\nAll {len(targets)} report file(s) valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
