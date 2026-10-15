#!/usr/bin/env python3
"""
Build html/archive/manifest.json from dated archive pages.

Each html/archive/YYYY-MM-DD.html is expected to contain a `const REPORT = { ... };`
object with the same schema used by the daily dashboard. We parse that object with a
permissive JS-to-JSON converter and emit a lightweight searchable manifest.

Run:
    python scripts/build_manifest.py
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_DIR = ROOT / "html" / "archive"
OUT = ARCHIVE_DIR / "manifest.json"

DATE_FILE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})\.html$")
REPORT_RE = re.compile(r"const\s+REPORT\s*=\s*(\{.*?\})\s*;\s*\n", re.DOTALL)


def js_object_to_json(src: str) -> str:
    """
    Convert a JS object literal (as used inline in the dashboard) to JSON.
    Handles:
      - unquoted keys
      - single-quoted strings
      - trailing commas
      - // line comments and /* block */ comments
      - template literals (treated as plain strings)
    """
    # Strip block comments
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.DOTALL)
    # Strip line comments (but not inside strings — our data has no // in strings)
    src = re.sub(r"(^|[^:])//[^\n]*", r"\1", src)

    out = []
    i = 0
    n = len(src)
    while i < n:
        c = src[i]

        # Double-quoted string — copy verbatim
        if c == '"':
            j = i + 1
            while j < n:
                if src[j] == "\\":
                    j += 2
                    continue
                if src[j] == '"':
                    j += 1
                    break
                j += 1
            out.append(src[i:j])
            i = j
            continue

        # Single-quoted string — convert to double-quoted JSON string
        if c == "'":
            j = i + 1
            buf = []
            while j < n:
                if src[j] == "\\":
                    buf.append(src[j:j + 2])
                    j += 2
                    continue
                if src[j] == "'":
                    j += 1
                    break
                buf.append(src[j])
                j += 1
            inner = "".join(buf).replace('"', '\\"')
            out.append('"' + inner + '"')
            i = j
            continue

        # Template literal — treat as plain string (no ${} expected in data)
        if c == "`":
            j = i + 1
            buf = []
            while j < n:
                if src[j] == "\\":
                    buf.append(src[j:j + 2])
                    j += 2
                    continue
                if src[j] == "`":
                    j += 1
                    break
                buf.append(src[j])
                j += 1
            inner = "".join(buf).replace('"', '\\"').replace("\n", "\\n")
            out.append('"' + inner + '"')
            i = j
            continue

        out.append(c)
        i += 1

    s = "".join(out)

    # Quote unquoted object keys:  key:  →  "key":
    s = re.sub(r"([{,]\s*)([A-Za-z_][A-Za-z0-9_]*)\s*:", r'\1"\2":', s)

    # Remove trailing commas before } or ]
    s = re.sub(r",(\s*[}\]])", r"\1", s)

    return s


def parse_report(html: str) -> dict | None:
    m = REPORT_RE.search(html)
    if not m:
        return None
    blob = m.group(1)
    try:
        return json.loads(js_object_to_json(blob))
    except json.JSONDecodeError as e:
        print(f"  warn: JSON decode failed: {e}", file=sys.stderr)
        return None


def _collect_keywords(report: dict) -> list[str]:
    """Token set useful for substring search across a report."""
    bits: list[str] = []
    for s in report.get("spotlights") or []:
        for k in ("title", "headline", "summary", "relevance", "sourceLabel", "tag"):
            v = s.get(k)
            if v:
                bits.append(str(v))
        for b in s.get("bullets") or []:
            if b:
                bits.append(str(b))
    for s in list(report.get("energy") or []) + list(report.get("compliance") or []) + list(report.get("stories") or []):
        for k in ("title", "summary", "sourceLabel", "tag", "segment", "region"):
            v = s.get(k)
            if v:
                bits.append(str(v))
    return bits


def summarize_entry(date: str, report: dict) -> dict:
    spotlights = report.get("spotlights") or []
    stories = report.get("stories") or []
    energy = report.get("energy") or []
    compliance = report.get("compliance") or []

    # Lead title/summary = first spotlight (uses 'title' or legacy 'headline'),
    # else first story.  Summary falls back to first bullet for the new shape.
    lead = (spotlights[0] if spotlights else (stories[0] if stories else {})) or {}
    title = lead.get("title") or lead.get("headline") or f"Daily AI Intel — {date}"
    summary = lead.get("summary") or ""
    if not summary:
        bullets = lead.get("bullets") or []
        if bullets and isinstance(bullets[0], str):
            summary = bullets[0]

    # Unique tags across the report
    tags = []
    seen = set()
    for item in list(spotlights) + list(energy) + list(compliance) + list(stories):
        t = (item or {}).get("tag")
        if t and t not in seen:
            seen.add(t)
            tags.append(t)

    sources = []
    sseen = set()
    for item in list(spotlights) + list(energy) + list(compliance) + list(stories):
        lbl = (item or {}).get("sourceLabel")
        if lbl and lbl not in sseen:
            sseen.add(lbl)
            sources.append(lbl)

    return {
        "date": date,
        "url": f"{date}.html",
        "title": title,
        "summary": summary,
        "tags": tags,
        "sources": sources,
        "spotlight_count": len(spotlights),
        "story_count": len(stories),
        "energy_count": len(energy),
        "compliance_count": len(compliance),
        "keywords": _collect_keywords(report)[:40],
    }


def main() -> int:
    if not ARCHIVE_DIR.is_dir():
        print(f"Archive dir missing: {ARCHIVE_DIR}", file=sys.stderr)
        return 1

    entries = []
    files = sorted(ARCHIVE_DIR.glob("*.html"))
    for f in files:
        m = DATE_FILE_RE.match(f.name)
        if not m:
            continue  # skip index.html and anything else
        date = m.group(1)
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            print(f"  skip {f.name}: invalid date", file=sys.stderr)
            continue

        html = f.read_text(encoding="utf-8")
        report = parse_report(html)
        if report is None:
            # Fallback: still index the date so it's reachable
            entries.append({
                "date": date,
                "url": f"{date}.html",
                "title": f"Daily AI Intel — {date}",
                "summary": "(Unable to extract structured summary from HTML.)",
                "tags": [],
                "sources": [],
                "spotlight_count": 0,
                "story_count": 0,
                "keywords": [],
            })
            continue

        entries.append(summarize_entry(date, report))

    # Newest first
    entries.sort(key=lambda e: e["date"], reverse=True)

    manifest = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "count": len(entries),
        "entries": entries,
    }

    OUT.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT.relative_to(ROOT)} with {len(entries)} entries.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
