# Contributing

## UI pull requests

A pull request that changes a user-visible interface is not done, and must not be merged, unless the PR body includes one of:

- browser screenshots of the changed states, or
- render-check output: the command, a zero exit status, and the log or a link to it

In this repo the render check is `node scripts/render_check.cjs`, run the way `.github/workflows/validate.yml` runs it (serve `html/`, then check today and the archive pages). A green badge alone does not count when that step did not run or the log is not linked from the PR.

Reviewers reject a UI pull request that is missing that evidence.

Non-UI changes (docs that do not change a rendered page, CI-only, tooling) say "No UI change" and omit the evidence.

The author does not review their own pull request.
