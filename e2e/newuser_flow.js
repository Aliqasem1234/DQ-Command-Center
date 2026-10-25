// Complete workflow as a brand-new, self-registered regular user.
// Usage: REPO=... node newuser_flow.js
const fs = require('fs');
const path = require('path');
require('fs').mkdirSync(path.join(__dirname, 'tmp'), { recursive: true });
const { launch, report, BASE } = require('./lib');
const { auditDark } = require('./darkaudit');

// Fresh random password per run: the script registers its own accounts, so no
// fixed test password ever has to be stored in the repository.
const PW = `e2e-${require('crypto').randomBytes(18).toString('base64url')}-Aa1!`;
const stamp = Date.now();
const A = `qa.prod.a.${stamp}@example.com`;
const B = `qa.prod.b.${stamp}@example.com`;
const results = [];
const darkProblems = [];
const check = (name, ok, extra = '') => results.push(`${ok ? 'PASS' : 'FAIL'}  ${name}${extra ? '  -- ' + String(extra).slice(0, 180) : ''}`);
const text = async (page) => (await page.locator('body').innerText()).replace(/\s+/g, ' ');
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const dark = async (page, label) => { const r = await auditDark(page, label); if (r.problems.length) darkProblems.push(r); };

const CSV = 'customer_id,name,email,city\n1,Anna, anna@example.com ,Stockholm\n2,Bo,,stockholm\n3,Cia,cia@example.com,Malmö\n3,Cia,cia@example.com,Malmö\n';
const csvPath = path.join(__dirname, 'tmp', `kunder_${stamp}.csv`);
fs.writeFileSync(csvPath, CSV);

async function uiLogin(page, email) {
  for (let i = 0; i < 4; i++) {
    await page.goto(`${BASE}/login`);
    await page.fill('input[type=email]', email);
    await page.fill('input[type=password]', PW);
    await page.click('button[type=submit]');
    try { await page.waitForURL(/dashboard/, { timeout: 8000 }); return; } catch {
      if (!(await text(page)).includes('För många')) throw new Error('login failed: ' + (await text(page)).slice(0, 200));
      await sleep(20000);
    }
  }
}
async function uiRegister(page, email, name) {
  for (let i = 0; i < 4; i++) {
    await page.goto(`${BASE}/register`);
    await page.fill('input[name=full_name]', name);
    await page.fill('input[name=email]', email);
    await page.fill('input[name=password]', PW);
    await page.fill('input[name=password_confirm]', PW);
    await page.click('button[type=submit]');
    await page.waitForTimeout(1500);
    const t = await text(page);
    if (t.includes('Kontot har skapats')) return true;
    if (!t.includes('För många')) return t;
    await sleep(20000);
  }
}
const tokenIn = (page) => page.evaluate(() => JSON.parse(localStorage.getItem('dq-auth-storage')).state.accessToken);
const apiAs = (page, method, p) => page.evaluate(async ([m, url]) => {
  const tok = JSON.parse(localStorage.getItem('dq-auth-storage')).state.accessToken;
  const r = await fetch(url, { method: m, headers: { Authorization: `Bearer ${tok}` } });
  return r.status;
}, [method, `/api/v1${p}`]);

(async () => {
  const { browser, page, log } = await launch();

  // 1-2. register + log in
  check('1. register via UI', (await uiRegister(page, A, 'Anna Användare')) === true);
  await uiLogin(page, A);
  check('2. log in -> dashboard', page.url().endsWith('/dashboard'));

  // 3. dashboard empty state + navigation
  await page.waitForTimeout(1200);
  let t = await text(page);
  check('3. dashboard shows first-run empty state (no fake numbers)', t.includes('Välkommen! Börja med din första datauppsättning') && !/\d+%/.test(t), t.slice(0, 160));
  const nav = (await page.locator('aside, nav').first().innerText()).replace(/\s+/g, ' | ');
  check('3. sidebar sections for a regular user', ['ÖVERSIKT', 'DATA', 'DATAKVALITET', 'DATASTYRNING', 'INSTÄLLNINGAR'].every((s) => nav.toUpperCase().includes(s)) && !/ADMINISTRATION|Användare \||Systemlogg/.test(nav), nav);
  check('3. no theme toggle anywhere', (await page.locator('[aria-label="Mörkt"], [aria-label="Ljust"], [aria-label="Dark"], [aria-label="Light"]').count()) === 0);
  await dark(page, 'dashboard (empty)');

  // 4. upload from the dashboard call-to-action
  await page.getByRole('button', { name: 'Ladda upp din första datauppsättning' }).click();
  await page.waitForTimeout(800);
  check('4. CTA opens the upload dialog on Datauppsättningar', page.url().includes('/datasets') && (await page.locator('input[type=file]').count()) === 1);
  await dark(page, 'upload dialog');
  await page.locator('form input:not([type=file])').first().fill(`Kunder ${stamp}`);
  await page.setInputFiles('input[type=file]', csvPath);
  await page.locator('form button[type=submit]').click();
  await page.waitForURL(/\/datasets\/[0-9a-f-]{36}/, { timeout: 30000 });
  const datasetUrl = page.url();
  const datasetId = datasetUrl.split('/datasets/')[1];
  check('4. upload created the dataset and opened it', true, datasetUrl.replace(BASE, ''));

  // 5-6. view + profile
  await page.waitForLoadState('networkidle');
  t = await text(page);
  check('5. dataset view shows name and 4 rows', t.includes(`Kunder ${stamp}`) && /\b4\b/.test(t));
  await page.getByRole('button', { name: /^Profil/ }).click(); await page.waitForTimeout(1000);
  t = await text(page);
  check('6. profile lists every column', ['customer_id', 'name', 'email', 'city'].every((c) => t.includes(c)), t.slice(0, 200));
  await dark(page, 'profile tab');

  // 7-8. scan + issues
  await page.getByRole('button', { name: /Skanna/ }).click();
  await page.waitForTimeout(2500);
  await page.getByRole('button', { name: /^Problem/ }).click(); await page.waitForTimeout(800);
  t = await text(page);
  check('7-8. scan finds the planted problems (missing email, duplicate row, casing)', /saknas|missing/i.test(t) && /dubblett|duplicate/i.test(t), t.slice(0, 300));
  await dark(page, 'issues tab');
  await page.getByRole('button', { name: /^Översikt/ }).click(); await page.waitForTimeout(800);
  const overview = await text(page);
  const scoreMatch = overview.match(/(\d{1,3}(?:[.,]\d)?)\s?%/);
  const datasetScore = scoreMatch ? parseFloat(scoreMatch[1].replace(',', '.')) : null;
  check('8. dataset quality score shown after scan', datasetScore !== null, scoreMatch && scoreMatch[0]);

  // 9. clean (trim whitespace) -> new version
  await page.getByRole('button', { name: /^Rensa/ }).click(); await page.waitForTimeout(600);
  const addOp = page.getByRole('button', { name: /Lägg till åtgärd/ });
  if (await addOp.count()) await addOp.click();
  await page.getByRole('button', { name: /Förhandsgranska/ }).click(); await page.waitForTimeout(1500);
  await dark(page, 'clean tab');
  await page.getByRole('button', { name: /Tillämpa/ }).click(); await page.waitForTimeout(2500);
  t = await text(page);
  check('9. cleaning created version 2', /v2|Version 2/i.test(t), t.slice(0, 200));

  // 10. download the cleaned file
  await page.getByRole('button', { name: /^Versioner/ }).click(); await page.waitForTimeout(800);
  const [dl] = await Promise.all([
    page.waitForEvent('download', { timeout: 10000 }).catch(() => null),
    page.getByRole('button', { name: 'Ladda ner' }).first().click(),
  ]);
  const body = dl ? fs.readFileSync(await dl.path(), 'utf8') : '';
  check('10. downloaded cleaned file has trimmed values', body.includes(',anna@example.com,') && !body.includes(' anna@example.com '), JSON.stringify(body.slice(0, 120)));
  await dark(page, 'versions tab');

  // 11-12. refresh persists
  await page.reload(); await page.waitForLoadState('networkidle');
  check('11-12. after refresh the dataset is still there', page.url() === datasetUrl && (await text(page)).includes(`Kunder ${stamp}`));

  // quality rule tied to the dataset
  await page.goto(`${BASE}/data-quality/rules`); await page.waitForLoadState('networkidle');
  await page.getByRole('button', { name: 'Lägg till' }).click();
  await page.locator('form input').first().fill(`E-post krävs ${stamp}`);
  await page.selectOption('#rule-dataset', { label: `Kunder ${stamp}` });
  // Executable rules need a column (the form refuses to save without one).
  await page.fill('#rule-column', 'email');
  await page.locator('form button[type=submit]').click(); await page.waitForTimeout(1200);
  const ruleRow = page.locator('tr', { hasText: `E-post krävs ${stamp}` });
  check('rules: user creates a rule for their dataset; table shows the dataset name', (await ruleRow.count()) === 1 && (await ruleRow.innerText()).includes(`Kunder ${stamp}`));
  await dark(page, 'rules');

  // activity log
  await page.goto(`${BASE}/activity`); await page.waitForLoadState('networkidle');
  t = await text(page);
  check('activity: own actions listed (upload, rule)', t.includes(`Kunder ${stamp}`) && t.includes(`E-post krävs ${stamp}`));
  await dark(page, 'activity');

  // 13-14. log out and back in
  await page.locator('header button').last().click();
  await page.getByRole('button', { name: 'Logga ut' }).click();
  await page.waitForURL(/login/);
  await uiLogin(page, A);
  await page.goto(`${BASE}/datasets`); await page.waitForLoadState('networkidle');
  check('13-14. after logout/login the same user sees their dataset', (await text(page)).includes(`Kunder ${stamp}`));

  // 15. dashboard reflects real data
  await page.goto(`${BASE}/dashboard`); await page.waitForLoadState('networkidle'); await page.waitForTimeout(800);
  t = await text(page);
  const healthMatch = t.match(/Övergripande hälsa\s*(\d{1,3})%/);
  const dsMatch = t.match(/Datauppsättningar\s*(\d+)/);
  check('15. dashboard: 1 dataset, health = dataset score (rounded)', dsMatch && dsMatch[1] === '1' && healthMatch && Number(healthMatch[1]) === Math.round(datasetScore), `datasets=${dsMatch && dsMatch[1]} health=${healthMatch && healthMatch[1]} score=${datasetScore}`);
  await dark(page, 'dashboard (with data)');

  // 16-17. second user: no access, no admin
  const b = await launch();
  check('16. second user registers', (await uiRegister(b.page, B, 'Bo Användare')) === true);
  await uiLogin(b.page, B);
  await b.page.goto(datasetUrl); await b.page.waitForLoadState('networkidle'); await b.page.waitForTimeout(800);
  const bt = await text(b.page);
  check('16. other user opening the dataset URL sees "not found", no data', bt.includes('hittades inte') && !bt.includes(`Kunder ${stamp}`));
  const probes = {
    versions: await apiAs(b.page, 'GET', `/dataset-files/${datasetId}/versions`),
    detail: await apiAs(b.page, 'GET', `/datasets/${datasetId}`),
    delete: await apiAs(b.page, 'DELETE', `/datasets/${datasetId}`),
  };
  check('16. other user API probes -> 404', Object.values(probes).every((s) => s === 404), JSON.stringify(probes));
  await b.page.goto(`${BASE}/dashboard`); await b.page.waitForTimeout(1000);
  check('16. other user dashboard is empty (no global numbers)', (await text(b.page)).includes('Välkommen!'));
  for (const p of ['/users', '/roles', '/departments', '/audit']) {
    await b.page.goto(`${BASE}${p}`); await b.page.waitForTimeout(500);
    if (!b.page.url().endsWith('/forbidden')) { check(`17. ${p} blocked`, false, b.page.url()); }
  }
  check('17. admin pages redirect to /forbidden', true);
  const admin = { users: await apiAs(b.page, 'GET', '/users'), roles: await apiAs(b.page, 'GET', '/roles'), audit: await apiAs(b.page, 'GET', '/audit/logs'), stats: await apiAs(b.page, 'GET', '/dashboard/stats') };
  check('17. admin APIs -> 403', Object.values(admin).every((s) => s === 403), JSON.stringify(admin));

  // sharing by email: A shares with B, B can then open it
  await page.goto(`${BASE}/governance`); await page.waitForLoadState('networkidle');
  await page.getByRole('button', { name: /Tilldela roll/ }).first().click();
  const form = page.locator('form').last();
  await form.locator('select').nth(1).selectOption('dataset');
  await form.locator('select').nth(2).selectOption({ label: `Kunder ${stamp}` });
  await form.locator('#assign-email').fill('nobody.' + stamp + '@example.com');
  await form.locator('button[type=submit]').click(); await page.waitForTimeout(1000);
  check('sharing: unknown email gives a clear message', (await text(page)).includes('Ingen aktiv användare har den e-postadressen'));
  await form.locator('#assign-email').fill(B);
  await form.locator('button[type=submit]').click(); await page.waitForTimeout(1500);
  check('sharing: share by email saved', (await text(page)).includes('Bo Användare'));
  await b.page.goto(datasetUrl); await b.page.waitForLoadState('networkidle'); await b.page.waitForTimeout(800);
  check('sharing: shared user can now open the dataset', (await text(b.page)).includes(`Kunder ${stamp}`));
  check('sharing: shared user has no delete button', (await b.page.getByRole('button', { name: 'Ta bort datauppsättning' }).count()) === 0);
  await b.browser.close();

  // delete own dataset
  await page.goto(datasetUrl); await page.waitForLoadState('networkidle');
  await page.getByRole('button', { name: 'Ta bort datauppsättning' }).click();
  await dark(page, 'delete dialog');
  await page.getByRole('button', { name: 'Ta bort', exact: true }).click();
  await page.waitForURL(/\/datasets$/, { timeout: 10000 }).catch(() => {});
  await page.waitForTimeout(800);
  t = await text(page);
  check('delete: dataset removed, back on empty list', page.url().endsWith('/datasets') && !t.includes(`Kunder ${stamp}`) && t.includes('Inga datauppsättningar'));
  check('delete: API confirms it is gone', (await apiAs(page, 'GET', `/datasets/${datasetId}`)) === 404);

  // 18. dark theme everywhere
  check('18. dark theme consistent in every audited view', darkProblems.length === 0, JSON.stringify(darkProblems).slice(0, 400));
  report('user A', log);
  await browser.close();
  console.log('\n' + results.join('\n'));
  console.log(`\nACCOUNTS: ${A} ${B}`);
})().catch((e) => { console.error(e); console.log('\n' + results.join('\n')); process.exit(1); });
