# CLAUDE.md — Hand-off for Claude Code

> This file is the operating handbook for an AI coding agent (Claude Code) running the daily AI News Dashboard pipeline. The previous owner was a Perplexity Computer scheduled task. As of 2026-05-13 that task is deleted; this repo's daily edition is now driven from Claude Code.
>
> **Source of truth ordering:** this file > `README.md` > stored agent task descriptions. If anything conflicts, follow `CLAUDE.md`, then `README.md`.

> **2026-10-14 override:** the daily edition is now PR-gated and owned by Babbage — see README "Ownership & PR gate". Ignore the direct-push-to-main steps below.

---

## TL;DR — Daily Run

Run once per day, ideally between 04:00–05:00 ET so the new edition is live by morning.

```bash
cd /home/user/workspace/ai-news-dashboard
git checkout main && git pull --ff-only origin main
# (research → build REPORT object → atomic swap into html/index.html)
cp html/index.html "html/archive/$(date -u +%F).html"
# (apply archive-page adjustments)
python3 scripts/build_manifest.py
npx --yes html-validate@8 'html/**/*.html'     # MUST exit 0
git checkout -b "daily/$(date -u +%F)"
git add html/ scripts/
git commit -m "daily($(date -u +%F)): today's edition"
git checkout main && git merge --ff-only "daily/$(date -u +%F)"
git push origin main
git push origin --delete "daily/$(date -u +%F)" || true
```

A push to `main` touching `html/**` triggers `.github/workflows/deploy.yml`, which `aws s3 sync`s `html/` and invalidates CloudFront `/*`. Live in ~1–2 minutes at:

- https://news.harmonygrid.ai
- https://news.groovegrid.ai

---

## Repo Map

| Path | Purpose |
|---|---|
| `html/index.html` | Live dashboard. Contains the `REPORT` JS object literal that the page renders. |
| `html/archive/YYYY-MM-DD.html` | Per-day archived snapshot of that day's `index.html` with 4 page tweaks (see below). |
| `html/archive/index.html` | Archive browser (client-side substring search across all snapshots). |
| `html/archive/manifest.json` | Generated. Used by the archive browser. Rebuilt by `scripts/build_manifest.py`. |
| `scripts/build_manifest.py` | Walks `html/archive/*.html`, parses each REPORT, emits `manifest.json` `{generated_at, count, entries[]}`. Checks both `headline` (spotlights) and `title` (stories) when picking the lead title. |
| `.github/workflows/deploy.yml` | On push to `main` touching `html/**` or `scripts/build_manifest.py`: `aws s3 sync` + CloudFront invalidate. |
| `.github/workflows/validate.yml` | On PR touching `html/**` or `scripts/build_manifest.py` or `.htmlvalidate.json` or itself: runs `npx html-validate@8`. |
| `.htmlvalidate.json` | Lint config. Extends `html-validate:recommended` with these disabled: `no-inline-style`, `no-trailing-whitespace`, `void-style`, `no-raw-characters`, `attr-quotes`. |
| `README.md` | Public/product-facing description + workflow notes. Authoritative for tag vocabulary and section rules. |
| `cron_tracking/4ab17d93/` (outside repo, in workspace) | Historical per-day source JSON and REPORT block snapshots from the deleted scheduled task. Useful reference for past editions. |

---

## REPORT Object — Schema & Editing

The page renders from a single JS object literal in `html/index.html`:

```js
const REPORT = {
  date: "YYYY-MM-DD",
  spotlights: [
    {
      headline: "...",
      summary: "...",
      tags: ["harmony" | "groove" | "both" | "enterprise" | "bonus"],
      bonus: true,        // REQUIRED on bonus items — render caps to 2 primary otherwise
      sourceLabel: "...",
      sourceUrl: "https://...",
    },
    // ...
  ],
  stories: [
    {
      title: "...",
      summary: "...",
      tags: [...],
      sourceLabel: "...",
      sourceUrl: "https://...",
    },
    // ...
  ],
};
```

**Required item counts per day:** 2 primary spotlights + 2 bonus spotlights + 5–7 stories. Every item needs a real `sourceLabel` + `sourceUrl`.

**Tag vocabulary:** `groove`, `harmony`, `both`, `enterprise`, `bonus`. Bonus items MUST also set `bonus: true` (the tag alone isn't enough — the render caps primary spotlights to 2 otherwise).

**Bucket coverage** (the five research lanes that feed REPORT):
- (a) HEMS / VPP / OpenADR / grid-edge / DERMS / demand response → `harmony` + `groove`
- (b) enterprise AI platforms / agent frameworks / agent governance / identity → `enterprise`
- (c) open-weight LLMs / Ollama / LM Studio / self-hosted stacks → `harmony`
- (d) AI property management / real estate tools → `groove`
- (e) creator / AI music / AI video → `bonus`

### Atomic REPORT swap — REQUIRED

Multiline diffs and naive find/replace on the REPORT block have failed in production multiple times (the edit replaces the entire object with a partial fragment, leaving the file invalid). Use this exact Python pattern instead — no exceptions:

```python
import re

with open('html/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Match `const REPORT = {` through the closing `};` line. DOTALL + non-greedy.
pattern = re.compile(r'const REPORT = \{.*?\n\};\n', re.DOTALL)
matches = pattern.findall(html)

# Hard guards — fail the run if either fires; do NOT fall back to a textual diff.
assert len(matches) == 1, f'expected 1 REPORT block, found {len(matches)}'
assert 'TAG_META' not in matches[0], 'pattern over-matched into TAG_META'

# str.replace, NOT re.sub — re.sub interprets backslash escapes (e.g. \u) in the
# replacement string and corrupts unicode in the new REPORT text.
new_html = html.replace(matches[0], new_report_text, 1)

with open('html/index.html', 'w', encoding='utf-8') as f:
    f.write(new_html)
```

Also update the dateline elsewhere in `html/index.html` (search for the date string near `#report-date`).

### Post-write structural validation

Both MUST pass before commit:

1. `npx --yes html-validate@8 'html/**/*.html'` exits 0.
2. The new REPORT block parses and contains `date`, `spotlights`, `stories` keys.

If either fails: **abort, do not push**, write a note to `cron_tracking/4ab17d93/` (or new `handoff_log/`) describing what broke.

---

## Archive-Page Adjustments

After `cp html/index.html html/archive/YYYY-MM-DD.html`, apply these 4 edits to the archive copy. Reference `html/archive/2026-04-22.html` for the exact pattern.

1. **Brand span** — append ` · Archived`:
   - Find: `<span class="brand">...</span>`
   - Replace with: `<span class="brand">... · Archived</span>`

2. **Header right-nav** — replace single Archive button with TWO buttons:
   - Find: `<a class="archive-link" href="archive/" title="Browse prior days">Archive</a>` (or similar — the live page's archive link)
   - Replace with both:
     ```html
     <a class="archive-link" href="../" title="Latest edition">Latest</a>
     <a class="archive-link" href="index.html" title="Archive index">Archive</a>
     ```

3. **Insert archive banner** — immediately after `</header>`:
   ```html
   <div class="archive-banner">
     This is an archived edition. <a href="../">View today's edition</a> · <a href="index.html">Browse archive</a>
   </div>
   ```

4. **Add `.archive-banner` CSS rule** — before `#report-date` in the stylesheet:
   ```css
   .archive-banner {
     max-width: 1100px;
     margin: 12px auto;
     padding: 10px 14px;
     border-left: 3px solid var(--bonus);
     font-size: 0.9rem;
     color: var(--muted);
   }
   .archive-banner a { color: inherit; text-decoration: underline; }
   ```

---

## Research Window — Signal Over Recency

**Default: past 7 days. Prefer past 48h when available. Optimize for signal over recency.**

A high-signal item from earlier in the week is better than a thin last-24h filler. Do not block the daily run because the last 24h is "thin" — that's the whole reason the window is 7 days.

Acceptable story sources include:
- Press releases, vendor blogs, regulator filings
- Changelog entries (Runway, Luma, LM Studio, Ollama, etc.)
- Industry benchmark reports (e.g. AppFolio)
- Reputable trade press (Utility Dive, Commercial Observer, Reworked, etc.)
- Research write-ups

A B+ edition deployed beats an A+ edition stuck waiting for "more news."

**Only stop the run on real pipeline breaks:**
- `html-validate` non-zero exit
- Atomic-swap guards fail (no match, multiple matches, `TAG_META` over-match)
- `git push` fails
- Total source famine after 7-day widening across all 5 buckets (this should essentially never happen)

---

## Workflow Sequence (Detailed)

1. `cd /home/user/workspace/ai-news-dashboard && git checkout main && git pull --ff-only origin main`
2. Re-read this file and `README.md`. README is authoritative for product/section rules; this file is authoritative for operational mechanics.
3. Research with parallel web searches across the 5 buckets. Default window = past 7 days.
4. Build the REPORT object: 2 primary spotlights + 2 bonus + 5–7 stories.
5. `git checkout -b daily/YYYY-MM-DD`
6. Edit `html/index.html` via the atomic REPORT swap. Update dateline.
7. `cp html/index.html html/archive/YYYY-MM-DD.html` and apply the 4 archive-page adjustments.
8. `python3 scripts/build_manifest.py` to regenerate `html/archive/manifest.json`.
9. `npx --yes html-validate@8 'html/**/*.html'` — must exit 0. Assert REPORT contains `date`/`spotlights`/`stories`.
10. Commit:
    ```
    daily(YYYY-MM-DD): today's edition

    Spotlights:
    - [tag] Headline (sourceUrl)
    - [tag] Headline (sourceUrl)
    Bonus:
    - [tag,bonus] Headline (sourceUrl)
    - [tag,bonus] Headline (sourceUrl)
    Stories: <count>
    ```
11. Push directly to `main` (no draft PR, no review gate):
    ```bash
    git checkout main
    git merge --ff-only daily/YYYY-MM-DD
    git push origin main
    git push origin --delete daily/YYYY-MM-DD || true
    ```
12. Verify deploy: poll the CloudFront URL or check `gh run list --workflow=deploy.yml --limit 1` until success.

---

## Environment & Auth

- **Local workspace:** `/home/user/workspace/ai-news-dashboard`
- **GitHub remote:** `https://github.com/mojosailor/ai-news-dashboard`
- **Git identity in workspace:** `user.email=rlovell@prevwind.com`, `user.name=mojosailor`
- **AWS account:** `992382519644`
- **S3 bucket:** `ai-news-dashboard-992382519644`
- **Deploy IAM role:** `arn:aws:iam::992382519644:role/ai-news-dashboard-deploy` (used by `deploy.yml` via OIDC)
- **Region:** `us-east-1`
- **gh / git auth:** Use the GitHub connector / token available in the environment. In Perplexity Computer that meant `api_credentials=['github']`; in Claude Code use whatever GitHub auth Claude Code is configured with (PAT or `gh auth`).

Never run `gh auth status` — it is known to fail in some environments and the auth check isn't needed if normal `gh` commands work.

---

## What's Been Tried — Lessons Pinned

- **Multiline diff on REPORT block fails.** Twice replaced the whole object with a partial fragment. Use the atomic Python pattern above. (See repo PR #14.)
- **`re.sub` corrupts unicode escapes** in the replacement string (`\u...`). Always use `str.replace(old, new, 1)`.
- **Thin last-24h cycles are normal.** Don't stop. Use the 7-day window.
- **`fetch_url` on the GitHub-hosted README can fail with `bad_robots_code`.** Read the local `README.md` instead.
- **The validator config exists because** the original `nickersoft/html-validate-action` is gone. We use `npx html-validate@8` + minimal `.htmlvalidate.json`. (See PR #7.)
- **Manifest builder picks lead title** from `headline` (spotlight) then `title` (story). PR #6 fixed an earlier crash on story-led days.
- **PRs are no longer the review gate.** The daily edition pushes straight to `main`. PRs were retired on 2026-05-01 per user direction.

---

## Failure Mode Playbook

| Symptom | Action |
|---|---|
| `html-validate` non-zero | Fix the offending file. Common: unclosed tags from a half-edit, missing alt text on a newly-added image. Re-run validator. |
| Atomic-swap guard: `expected 1 REPORT block, found 0` | Pattern didn't match. Either the file was corrupted by a prior edit or someone changed the REPORT declaration syntax. Inspect `html/index.html` around line 338. |
| Atomic-swap guard: `found 2` | A stray `const REPORT = {` exists somewhere else (e.g. in a comment or backup). Find and remove the duplicate. |
| Atomic-swap guard: `TAG_META over-match` | The regex captured too much. Likely the REPORT block contains a nested `};` followed by a newline. Tighten the pattern or refactor REPORT to keep the closing `};` on its own line. |
| `git push origin main` rejected (non-fast-forward) | Someone else pushed. `git fetch origin && git rebase origin/main`, re-validate, re-push. |
| Deploy workflow failed | Check `gh run view <run-id> --log-failed`. Usually AWS creds OIDC trust, S3 bucket name, or CloudFront distribution ID env var in the workflow. |
| Source famine after 7-day widening | Stop the run. Write a note to `handoff_log/YYYY-MM-DD-blocked.md` describing what was searched and why nothing met the bar. Do NOT push a half-built edition. |

---

## History

- **2026-04-20** Initial deploy via Perplexity Computer scheduled task (cron id `4ab17d93`, `0 8 * * *` UTC = 04:00 ET).
- **2026-04-22** First successful auto-deploy (PR-gated at the time).
- **2026-04-27** Atomic REPORT swap pattern adopted after a multi-line edit corrupted `index.html`.
- **2026-05-01** Switched from draft-PR-gated to direct push-to-main. README override notice added.
- **2026-05-13** Scheduled task deleted. Daily edition driven from Claude Code going forward.

Most recent editions visible at https://news.harmonygrid.ai/archive/.
