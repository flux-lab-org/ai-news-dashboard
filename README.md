# ai-news-dashboard


---

## Section Definitions

### Flux Spotlights
- Always ≥1 Flux spotlight per day.
- Each tagged: `[GrooveGrid]`, `[HarmonyGrid]`, or `[GrooveGrid + HarmonyGrid]`.
- Dual tag allowed when a development clearly benefits both brands.
- Priority triggers: HEMS, VPP, DERMS, OpenADR, submetering, CalTRACK/M&V,
  property management AI, energy incentives, demand/solar/EV forecasting.

### Enterprise Spotlights
- Always ≥1 general spotlight (unless Flux fills all slots on a big Flux day).
- Rotates through 10 core use cases (customer support, sales copilots, doc processing,
  personalization, fraud/risk, agentic automation, knowledge mgmt, supply chain, IT ops,
  industry-specific assistants).
- Format: short title + 2–4 bullets (value, tech pattern, what to pilot next).

### Spotlight Count Rules
| Condition                | Count         |
|---|---|
| Default                  | 2 (1 Flux + 1 General) |
| Multiple strong items    | Expand up to 4 total   |
| Hard cap                 | 4 spotlights max       |

Ranking when >4 candidates: Flux impact → Enterprise impact → Researcher novelty.

### For AI Researchers
- New model/architecture releases, arXiv links, evals.
- Frameworks, orchestrators, agent frameworks, eval harnesses.
- Benchmarks, safety, multi-modal eval news.
- Dataset & synthetic data tooling.
- Research productivity tools (Elicit, SciSpace, Julius, ScholarAI, etc.).

### Free Tools
- 3–5 bullets/day; genuinely free or free-tier.
- Format: what it does + free-tier limits + architecture slot note.
- Bias: Project Flux dev, Proxmox homelab, worship/studio workflows.

### Self-Hosting Trend Watch
- 3–5 bullets/day, tagged [home-lab ready] / [SMB-friendly] / [enterprise-grade].
- Covers: Ollama, LM Studio, Jan, LocalAI, oobabooga, GPT4All, Open WebUI,
  self-hosted agent frameworks, cloud vs self-hosted trends, GPU templates.

### Creator Tools
- 3–5 bullets/day across music/audio, video, and design.
- Music: song generation, stem separation, mastering, vocal tools → worship/studio use.
- Video: AI generators, auto-caption, smart cut → lyric reels, event promos, recaps.
- Design: text-to-image, Canva AI, Firefly, SD → Sunday graphics, series key art.

---

### Completely Absent
- tsconfig.json — no TypeScript setup. (A root `package.json`/`package-lock.json` exist as of FLU-1545, but only to pin CI's Playwright verification dependency — there is still no app build step, framework, or bundler.)
- pyproject.toml / requirements.txt — no Python package dependencies
- Makefile / Procfile — no task runners or process managers
- docker-compose.yml / Dockerfile — no containerization yet
- nv files — no environment variables defined
- te/Next.js/Nuxt configs — no frontend bundlers

## Ownership & PR gate (updated 2026-10-14)

- **Owner:** Babbage (flux-lab agent) owns the daily edition as of 2026-10-14, per Ron. Previous producers: Perplexity scheduled task (to 2026-05-13), Claude Code, then Cody's Paperclip digests (under [FLU-791](https://paperclip.flux-lab.ai/FLU/issues/FLU-791)).
- **Source:** the day's Paperclip digest issue (e.g. FLU-1269 for 2026-10-14) is converted into the `REPORT` object. Every link is re-verified before publishing; links that cannot be verified are called out in the PR.
- **PR gate restored:** editions now land via a `daily/YYYY-MM-DD` branch and a PR to `main`, reviewed by another agent, with a Paperclip ticket tracking the work (flux-lab `merge-deploy` house rules). This **supersedes** the 2026-05-01 "push directly to `main`, no review gate" instructions below and in `CLAUDE.md`.
- Paperclip digests are AI/enterprise-focused and may not include a Flux (`groove`/`harmony`) spotlight; the section rules below remain the target.

## Hand-offs / Infra Notes

Operational hand-offs (things that need to land in another repo, like `aws-master-tf`) live in [`docs/`](docs/README.md). Start there when an infra or cross-repo change is needed. The index lists each hand-off, its status, and the target repo so you don't have to grep for your name.

## Delivery Architecture

**Current state:** static HTML served from S3 behind CloudFront. Deployed by a GitHub Action on every push to `main` that touches `html/**` or `scripts/**`.

### Render contract & validation pipeline (added 2026-05-03)

Every `html/**.html` report page must contain a `const REPORT = {…};` literal that satisfies the schema below. The renderer in each page reads this object on load. **Schema drift between data and template was the root cause of the 2026-04-29 → 2026-05-02 blank-page incident** — the validators below exist so it cannot recur.

**REPORT schema (enforced by `scripts/validate_report.py`):**

- `date`: `YYYY-MM-DD` string, required.
- `spotlights`: non-empty array. Each entry must have:
  - `title` (string; legacy `headline` accepted for archive files only)
  - `tag`: one of `groove | harmony | both | enterprise | bonus`
  - `bullets`: non-empty array of strings (legacy `summary` string accepted as fallback)
  - `sourceUrl`: `http(s)://…`
  - `sourceLabel`: non-empty string
  - Optional: `bonus: true` for the bonus card slot, `keywords[]`, `relevance` string
- `stories`: array (may be empty). Each entry: `title`, `tag`, `sourceUrl`, `sourceLabel`.
- `energy`: **optional** array (added 2026-10-14). Same shape as `stories` (`title`, `tag`, `sourceUrl`, `sourceLabel`). Rendered in a dedicated **Energy** section between Spotlights and More Stories using the `.story-item` markup; the section is hidden when the array is empty or absent. Use it for residential/rental energy, utility programs, demand response, smart meters and rebates (e.g. Mass Save). An item may also appear as a spotlight (e.g. to satisfy the Flux-spotlight rule). Validated by `validate_report.py`, indexed by `build_manifest.py` (`energy_count`), and checked by `render_check.cjs` (rendered count must equal array length).
- `compliance`: **optional** array (added 2026-10-14). Regulatory & compliance items for small, mid-size and large/commercial landlords (building performance standards, benchmarking/disclosure, RUBS/submetering billing laws, electrification/EV mandates, rebate program rules). Each entry: `title`, `tag` (standard vocabulary, used for the pill colour), `segment` (`small | mid | large | all`), `region` (non-empty string), `sourceUrl`, `sourceLabel`; optional `summary` (1–2 lines: who is affected, by when, source + date) and `kind` (`in-window | in-effect | upcoming-deadline`). Rendered as a **Regulatory & Compliance** section after Energy (hidden when empty) using `.story-item` markup with a "kind · segment · region" prefix. Never invent deadlines: `upcoming-deadline` items must cite the official program page. Validated by `validate_report.py`, indexed by `build_manifest.py` (`compliance_count`), and checked by `render_check.cjs` (rendered count must equal array length).

**Three independent guards run before any deploy reaches production:**

1. **Markup validation** — `npx html-validate@8 html/**/*.html`.
2. **Schema validation** — `python scripts/validate_report.py` parses the embedded `REPORT` object out of every page and checks the contract above.
3. **Headless render check** — `node scripts/render_check.cjs <urls>` loads each page in real Chromium, fails on any uncaught JS error or `console.error`, and asserts `#spotlight-grid` has at least one `.card` and `#story-list` has at least one `.story-item` (or an explicit empty-state message).

All three run in `.github/workflows/validate.yml` on PRs and pushes to `main`, and again in `.github/workflows/deploy.yml` *before* `aws s3 sync` touches the bucket. The deploy job also waits for the CloudFront invalidation to complete and then re-runs the headless render check against `https://news.harmonygrid.ai` and `https://news.groovegrid.ai`. If that post-deploy smoke test fails, the previous `index.html` is restored from a snapshot taken just before the sync and CloudFront is invalidated again — production is never left in a blank state.

See `scripts/patch_render_template.py` for the one-shot patcher that brought every legacy archive onto the current renderer.

### Storage & layout

```
html/
├── index.html                   # today's dashboard (landing page)
└── archive/
    ├── index.html               # searchable prior-day browser
    ├── manifest.json            # auto-generated search index (do not edit by hand)
    ├── 2026-04-20.html          # snapshot per day, named YYYY-MM-DD.html
    └── …
```

URLs after deploy:
- `/`                           → today
- `/archive/`                   → searchable archive (text + date-range)
- `/archive/2026-04-20.html`    → a specific prior day
- `/archive/?q=HEMS&from=2026-04-01` → shareable pre-filtered search

### Daily update workflow (librarian)

Every day, produce the new dashboard then snapshot it.

**Research window (signal over recency).** Default to the past 7 days, prefer items from the past 48h when available, and optimize for signal over recency — a high-signal item from earlier in the week is better than a thin last-24h filler. This rule applies on every run; do not escalate just because the last 24h is thin. Cover all five buckets from the daily run instructions: (a) HEMS / VPP / OpenADR / DERMS / demand response, (b) enterprise AI platforms / agent governance / identity, (c) open-weight LLMs / Ollama / self-hosted, (d) AI property management / real estate, (e) creator / AI music / AI video. Aim for 2 primary spotlights + 2 bonus + 5–7 stories with the README tag vocabulary (`groove | harmony | both | enterprise | bonus`; bonus items must include `bonus: true`).

1. Update the `REPORT` object inside `html/index.html` with today's content. Set `REPORT.date` to today in `YYYY-MM-DD` format.

   **REQUIRED — atomic REPORT swap pattern.** Multiline diffs and large find/replace operations on the REPORT block have failed in production (the edit replaces the entire object with a partial fragment, leaving the file invalid). Daily automation runs MUST mutate the REPORT block using the exact Python pattern below — no exceptions:

   ```python
   import re

   with open('html/index.html', 'r', encoding='utf-8') as f:
       html = f.read()

   # Match the REPORT object literal from `const REPORT = {` through the closing `};` line.
   pattern = re.compile(r'const REPORT = \{.*?\n\};\n', re.DOTALL)
   matches = pattern.findall(html)

   # Hard guards — fail the run, do NOT fall back to a textual diff.
   assert len(matches) == 1, f'expected 1 REPORT block, found {len(matches)}'
   assert 'TAG_META' not in matches[0], 'pattern over-matched into TAG_META'

   # Use str.replace, NOT re.sub — re.sub interprets backslash escapes (e.g. \u) in the replacement
   # string and corrupts unicode in the new REPORT text.
   new_html = html.replace(matches[0], new_report_text, 1)

   with open('html/index.html', 'w', encoding='utf-8') as f:
       f.write(new_html)
   ```

   Post-write structural validation MUST also pass before commit:
   - `npx --yes html-validate@8 'html/**/*.html'` exits 0
   - The new REPORT block parses as a JS object literal containing `date`, `spotlights`, and `stories` keys

   If any guard fails, abort the run and send a notification — do not push a partially-edited file.

2. Copy the updated file into the archive with today's date:
   ```bash
   cp html/index.html "html/archive/$(date -u +%F).html"
   ```
3. (Optional, done automatically by CI) Regenerate the manifest:
   ```bash
   python scripts/build_manifest.py
   ```
4. Commit on `daily/YYYY-MM-DD`, push that branch, and open a PR to `main`. A non-author agent must review the edition and all validation checks must pass before merge. Standard daily editions may then be rebase-merged by the authorized reviewer; use an admin bypass only when explicitly authorized by the tracking issue. Never push or fast-forward an edition directly to `main`.

   ```bash
   git switch -c "daily/$(date -u +%F)" # omit if already on today's branch
   git add html/ scripts/
   git commit -m "daily(YYYY-MM-DD): today's edition"
   git push -u origin HEAD
   gh pr create --base main --title "Daily edition YYYY-MM-DD" --body-file review-notes.md
   ```

   Include source verification limits and the Paperclip tracking issue in the PR description. After independent approval and a passing validation workflow, merge through the PR. The resulting push to `main` triggers deployment, rebuilds the archive manifest, syncs `html/` to S3, and invalidates CloudFront. Verify the live edition date after deployment; a green workflow alone is insufficient.

   If any guard fails (atomic-swap assertions, `html-validate` non-zero exit, missing required REPORT keys, search bucket coverage clearly inadequate even after widening to 7 days), abort the run and send a notification — do not push a broken or empty file. Send the post-deploy `send_notification` (title: "Daily AI news deployed", body summarizing spotlights + tags, url: live site URL) on success.

The archive page is a pure client-side app: it fetches `manifest.json` and does substring search across each day's title, summary, tags, sources, and keywords (first spotlight + all stories). No server, no index service.

### Hosting Options (historical notes)

 This is a single static HTML file — a dark-themed dashboard with no build step, no framework, no backend. That makes
hosting dead simple. Here are your options from cheapest to most capable:

| Option | Cost | Effort | Best For |
|--------|------|--------|----------|
| here.now (Tailscale Funnel) | Free | Minimal — tailscale funnel /path/to/html | Private/team access via Tailscale, zero
config |
| GitHub Pages | Free | Push to repo, enable Pages | Public static site, auto-deploy on push |
| Cloudflare Pages | Free | Connect repo or wrangler pages deploy html/ | Public, global CDN, fast, custom domain |
| S3 + CloudFront | ~$0.50-1/mo | TF it — S3 bucket + CF distribution + Route53 | AWS-native, custom domain, you already
have the account |
| AWS Amplify Hosting | Free tier (5 GB/mo) | Connect repo or manual deploy | AWS-native, auto-builds on push, custom
domain, preview deploys |

### My recommendation

S3 + CloudFront if you want it in your AWS ecosystem — you already have account 332745420766 with Terraform, and it's a
single HTML file so the cost is essentially zero. I can write the TF module in aws-master-tf.

Cloudflare Pages if you want the fastest path with zero cost and don't care about AWS — npx wrangler pages deploy html/
and you're live.

Amplify is overkill for a single static HTML file with no build step, but makes sense if you plan to add a build
pipeline (e.g., a script that regenerates the dashboard daily and pushes to the repo).



---

## Related Files
- [[homelab-project-index.md]]
- [[projects/flux/architecture/multi-tenant-design.md]]
- [[projects/flux/research/2026-03-hems-market-landscape.md]]

---

## Change Log
| Date       | Version | Notes |
|---|---|---|
| 2026-04-20 | V1      | Initial brief. Task ID: 121fff15770d47d8840b57297aa1c509 |