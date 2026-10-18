const { chromium } = require('playwright-core');
const BASE = process.env.BASE || 'http://localhost';

async function launch({ lang = 'sv' } = {}) {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const context = await browser.newContext();
  await context.addInitScript((l) => { try { localStorage.setItem('i18nextLng', l); } catch {} }, lang);
  const page = await context.newPage();
  const log = { console: [], pageErrors: [], failed: [], http: [] };
  page.on('console', (m) => { if (['error', 'warning'].includes(m.type())) log.console.push(`[${m.type()}] ${m.text().slice(0, 300)}`); });
  page.on('pageerror', (e) => log.pageErrors.push(String(e).slice(0, 400)));
  page.on('requestfailed', (r) => log.failed.push(`${r.method()} ${r.url()} ${r.failure()?.errorText}`));
  page.on('response', (r) => { if (r.url().includes('/api/') && r.status() >= 400) log.http.push(`${r.status()} ${r.request().method()} ${r.url().replace(BASE, '')}`); });
  return { browser, context, page, log };
}

function report(name, log) {
  console.log(`--- ${name}`);
  for (const k of Object.keys(log)) if (log[k].length) console.log(`  ${k}:`, JSON.stringify(log[k], null, 1));
}

async function login(page, email, password) {
  await page.goto(`${BASE}/login`);
  await page.fill('input[type=email]', email);
  await page.fill('input[type=password]', password);
  await page.click('button[type=submit]');
  await page.waitForURL(/dashboard/, { timeout: 15000 });
}

module.exports = { launch, report, login, BASE };
