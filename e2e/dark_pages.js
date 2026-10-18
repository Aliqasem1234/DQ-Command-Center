// Run the dark-theme audit over every page and dialog. Usage: REPO=... node dark_pages.js
const fs = require('fs');
const path = require('path');
const { launch, login, BASE } = require('./lib');
const { auditDark } = require('./darkaudit');

const env = fs.readFileSync(path.join(process.env.REPO || path.resolve(__dirname, '..'), '.env'), 'utf8');
const get = (k) => (env.match(new RegExp(`^${k}=(.*)$`, 'm')) || [])[1]?.trim();

(async () => {
  const out = [];
  const record = (r) => out.push(r);
  const { browser, page } = await launch();
  // Simulate a user who had chosen the light theme before this release.
  await page.addInitScript(() => { try { localStorage.setItem('dq-theme-storage', JSON.stringify({ state: { mode: 'light' }, version: 0 })); } catch {} });

  for (const p of ['/login', '/register', '/forgot-password', '/reset-password?token=x', '/does-not-exist', '/forbidden']) {
    await page.goto(`${BASE}${p}`); await page.waitForTimeout(700);
    record(await auditDark(page, `public ${p}`));
  }
  await login(page, get('INIT_ADMIN_EMAIL'), get('INIT_ADMIN_PASSWORD'));
  const pages = ['/dashboard', '/datasets', '/data-quality/rules', '/data-quality/monitoring', '/governance', '/activity',
    '/profile', '/security', '/users', '/roles', '/departments', '/audit'];
  for (const p of pages) {
    await page.goto(`${BASE}${p}`); await page.waitForLoadState('networkidle'); await page.waitForTimeout(600);
    record(await auditDark(page, p));
  }
  // Dialogs and tabs
  const dialogs = [
    ['/datasets', 'button:has-text("Ladda upp datauppsättning")', 'dialog: upload'],
    ['/data-quality/rules', 'button:has-text("Lägg till")', 'dialog: new rule'],
    ['/governance', 'button:has-text("Tilldela roll")', 'dialog: assign role'],
    ['/users', 'button:has-text("Lägg till")', 'dialog: new user'],
    ['/roles', 'button:has-text("Lägg till")', 'dialog: new role'],
    ['/departments', 'button:has-text("Lägg till")', 'dialog: new department'],
  ];
  for (const [p, sel, label] of dialogs) {
    await page.goto(`${BASE}${p}`); await page.waitForLoadState('networkidle');
    await page.locator(sel).first().click(); await page.waitForTimeout(500);
    record(await auditDark(page, label));
  }
  await page.goto(`${BASE}/users`); await page.waitForLoadState('networkidle');
  await page.locator('button[aria-label="Ändra roller"]').nth(1).click(); await page.waitForTimeout(600);
  record(await auditDark(page, 'dialog: edit roles'));
  // user menu
  await page.goto(`${BASE}/dashboard`); await page.waitForTimeout(600);
  await page.locator('header button').last().click(); await page.waitForTimeout(300);
  record(await auditDark(page, 'menu: user'));
  // dataset detail tabs
  await page.goto(`${BASE}/datasets`); await page.waitForLoadState('networkidle');
  await page.locator('main button').filter({ hasText: /rader|rows/ }).first().click();
  await page.waitForLoadState('networkidle'); await page.waitForTimeout(800);
  for (const tab of ['Översikt', 'Profil', 'Problem', 'Rensa', 'Versioner']) {
    const b = page.getByRole('button', { name: new RegExp(`^${tab}`) });
    if (await b.count()) { await b.first().click(); await page.waitForTimeout(700); record(await auditDark(page, `dataset tab ${tab}`)); }
  }
  const del = page.getByRole('button', { name: 'Ta bort datauppsättning' });
  if (await del.count()) { await del.click(); await page.waitForTimeout(300); record(await auditDark(page, 'dialog: delete dataset')); await page.getByRole('button', { name: 'Avbryt' }).click(); }
  const themeKey = await page.evaluate(() => localStorage.getItem('dq-theme-storage'));
  await browser.close();

  let total = 0;
  for (const r of out) {
    total += r.problems.length;
    console.log(`${r.problems.length ? 'ISSUES' : 'OK    '} ${r.label}${r.problems.length ? '' : ''}`);
    for (const p of r.problems.slice(0, 8)) console.log('        ' + p);
    if (r.problems.length > 8) console.log(`        ... +${r.problems.length - 8} more`);
  }
  console.log(`\nchecked ${out.length} views, ${total} problems; old light preference left in storage: ${themeKey !== null}`);
})().catch((e) => { console.error(e); process.exit(1); });
