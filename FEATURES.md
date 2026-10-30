# FEATURES.md — ai-news-dashboard

Maps the dashboard's actual features to the exact checks/commands that verify them, and
is candid about what each check does and does not catch. Added under [FLU-1545].

[FLU-1545]: https://paperclip.flux-lab.ai/FLU/issues/FLU-1545

| Feature | Verified by | Command | What it actually checks | Known gap |
|---|---|---|---|---|
| HTML markup is well-formed | `validate.yml` / `deploy.yml` | `npx html-validate@8 "html/**/*.html"` | Markup validity (tags, attributes, nesting) across every page, today and archive. | Does not check rendered visual layout or content correctness. |
| `REPORT` object matches the content schema | `validate.yml` / `deploy.yml` | `python scripts/validate_report.py` | Every page's embedded `REPORT` JS object parses and matches the expected shape (spotlights, stories, energy, compliance, free tools, self-hosting, creator tools). Catches the "template renders nothing because data shape changed" class of bug before it ships. | Schema-only; does not check that the *content* is accurate or current. |
| Archive is enumerable and searchable | `validate.yml` / `deploy.yml` | `python scripts/build_manifest.py` then a JSON-load of `html/archive/manifest.json` | The manifest builder can parse every dated archive page's `REPORT` and emits valid JSON. | Does not check the manifest's search UI actually finds pages — see render check below for an indirect signal only. |
| Pages render without JS/console errors, on desktop and mobile | `validate.yml` / `deploy.yml` | `node scripts/render_check.cjs <urls...>` (served from a local `python -m http.server` over `html/`) | Loads the live index page **and every archive page matching `html/archive/2026-*.html`** (no case is silently skipped — the glob uses `nullglob` so a zero-match run doesn't try to curl a literal unexpanded pattern) in a real Chromium instance at both a 1280×800 desktop viewport and a 375×812 mobile viewport, and asserts: zero `pageerror`/`console.error` events, a non-blank body (>200 chars of visible text) on both viewports, `#spotlight-grid` has ≥1 `.card`, `#story-list` has ≥1 `.story-item` or an explicit empty-state marker, and the rendered energy/compliance list item counts match the `REPORT.energy`/`REPORT.compliance` array lengths. | **This is a render-correctness and non-blank check, not a visual-regression check.** It cannot catch "the page still renders but the colors/spacing/copy are visually wrong" — see Coverage Gaps below. |
| Visual evidence of what a change actually looks like | `validate.yml` (`render-check-screenshots` artifact) | Automatic: `render_check.cjs` writes one full-page PNG per (URL, viewport) to `render-check-screenshots/`, uploaded even if the check step fails (as long as a capture exists before the failing assertion). | Produces a human-reviewable screenshot per page/viewport for every PR and push run. | Screenshots are evidence for human review, not an automated pixel-diff — see Coverage Gaps. |
| Production deploy only ships a render-verified build | `deploy.yml` | Same `validate_report.py` / `html-validate` / `render_check.cjs` sequence, run again pre-deploy against the build about to ship | Blocks the S3 sync + CloudFront invalidation if any pre-deploy guard fails. | Pre-deploy checks run against the local served copy, not the post-sync S3/CloudFront copy. |
| Production stays render-correct after deploy | `deploy.yml` post-deploy smoke test | `node scripts/render_check.cjs $LIVE_URLS` against `news.harmonygrid.ai` / `news.groovegrid.ai` | Same render assertions, against the live CloudFront-fronted URLs, with automatic rollback of `index.html` on failure. | Smoke test only re-checks `index.html` + archive globs reachable at deploy time, not every historical archive page. |
| UI PRs carry render evidence | `CONTRIBUTING.md` + reviewer process | N/A (process control, not automated) | A human/reviewer convention requiring screenshots or render-check output in the PR body. | Not machine-enforced; relies on reviewer diligence. |

## Coverage gaps (candid)

- **No automated visual regression.** Screenshots are saved and uploaded for every run, but nothing diffs them against a baseline. A change that renders without errors but looks wrong (broken CSS, overlapping text, wrong color) will pass every automated check here. Catching that currently depends on a human looking at the uploaded `render-check-screenshots` artifact or the PR's manually-attached screenshots (per `CONTRIBUTING.md`).
- **No accessibility (a11y) checks.** `html-validate` checks markup validity, not WCAG contrast/ARIA/semantics.
- **No performance budget.** No Lighthouse/web-vitals check exists; a page could pass every check here while loading slowly.
- **No cross-browser matrix.** Render checks run on Chromium only; Firefox/Safari-only regressions would not be caught.
- **Archive coverage is glob-bounded to the `2026-*` prefix.** A page added under a different year prefix would not be picked up by `validate.yml`/`deploy.yml` without updating the glob — this is a known, intentional simplification, not a silent gap, but worth flagging for whoever edits this after 2026.
- **PR-triggered checks run on GitHub-hosted (`ubuntu-latest`) runners, not self-hosted.** This repo is public, and this org's accepted security architecture (`adr-github-v2.1-flux-lab-org-layer-cake.md` §4 "PR execution" and gate G3) requires that untrusted/PR-controlled code never execute on a privileged self-hosted runner, and no unprivileged self-hosted runner group is currently provisioned for this repo. Self-hosted execution was intentionally not added to the `pull_request` trigger for this reason — see the PR description for the full rationale and the decision this leaves open for the repo owner.

## Changelog

| Date | Author | Change |
|---|---|---|
| 2026-10-30 | Claude (Paperclip, FLU-1545) | Initial FEATURES.md: mapped existing + newly added checks, documented coverage gaps. |
