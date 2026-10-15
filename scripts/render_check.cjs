#!/usr/bin/env node
/**
 * Headless render check.
 *
 * Loads the given URL(s) in a real browser and asserts:
 *   1. No uncaught JavaScript errors.
 *   2. No console.error messages.
 *   3. #spotlight-grid contains at least one .card.
 *   4. #story-list either has at least one .story-item OR shows the explicit
 *      "No additional stories today." empty-state message (a story-less day
 *      should be rare but is allowed).
 *
 * Usage:
 *   node scripts/render_check.cjs <url1> [url2 ...]
 *
 * Exits non-zero on any failure and prints all violations.
 */
const { chromium } = require('playwright');

async function checkOne(url) {
  const browser = await chromium.launch();
  const ctx = await browser.newContext();
  const page = await ctx.newPage();
  const errors = [];
  page.on('pageerror', (e) => errors.push(`pageerror: ${e.message}`));
  page.on('console', (m) => { if (m.type() === 'error') errors.push(`console.error: ${m.text()}`); });

  try {
    const resp = await page.goto(url, { waitUntil: 'networkidle', timeout: 30000 });
    if (!resp || !resp.ok()) {
      errors.push(`HTTP ${resp ? resp.status() : 'no-response'} on ${url}`);
    }
    const counts = await page.evaluate(() => {
      const grid = document.getElementById('spotlight-grid');
      const list = document.getElementById('story-list');
      return {
        spotlights: grid ? grid.querySelectorAll('.card').length : 0,
        stories: list ? list.querySelectorAll('.story-item').length : 0,
        emptyStory: !!(list && list.querySelector('.empty')),
        // Optional Energy section: an empty/absent REPORT.energy is fine (section hidden);
        // a non-empty one must render one .story-item per entry.
        energyExpected: (typeof REPORT !== 'undefined' && REPORT && Array.isArray(REPORT.energy)) ? REPORT.energy.length : 0,
        energy: (document.getElementById('energy-list') || { querySelectorAll: () => [] }).querySelectorAll('.story-item').length,
        bodyLength: document.body ? document.body.innerText.length : 0,
      };
    });

    if (counts.spotlights < 1) {
      errors.push(`spotlight-grid empty: 0 cards rendered`);
    }
    if (counts.stories < 1 && !counts.emptyStory) {
      errors.push(`story-list empty without explicit empty-state message`);
    }
    if (counts.energy !== counts.energyExpected) {
      errors.push(`energy-list rendered ${counts.energy} items, REPORT.energy has ${counts.energyExpected}`);
    }
    if (counts.bodyLength < 200) {
      errors.push(`page body too short (${counts.bodyLength} chars) — likely blank`);
    }

    return { url, counts, errors };
  } finally {
    await browser.close();
  }
}

(async () => {
  const urls = process.argv.slice(2);
  if (urls.length === 0) {
    console.error('Usage: render_check.cjs <url1> [url2 ...]');
    process.exit(2);
  }

  let failed = 0;
  for (const u of urls) {
    const r = await checkOne(u);
    if (r.errors.length === 0) {
      console.log(`  ok  ${u}  (${r.counts.spotlights} spotlights, ${r.counts.energy} energy, ${r.counts.stories} stories)`);
    } else {
      failed++;
      console.error(`  FAIL  ${u}`);
      for (const e of r.errors) console.error(`    - ${e}`);
    }
  }

  if (failed > 0) {
    console.error(`\n${failed} URL(s) failed render check.`);
    process.exit(1);
  }
  console.log(`\nAll ${urls.length} URL(s) rendered successfully.`);
})().catch((e) => {
  console.error(`render_check fatal: ${e.message}`);
  process.exit(2);
});
