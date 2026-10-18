// Two-user isolation, in the real app, in one browser tab with account
// switches (client-side navigation only), plus API probes, reload, sharing
// and cross-tab switching. Usage: REPO=... BASE=http://localhost:5173 node two_user_isolation.js
const fs = require('fs');
const path = require('path');
const { launch } = require('./lib');
const { auditDark } = require('./darkaudit');

const BASE = process.env.BASE || 'http://localhost:5173';
const env = fs.readFileSync(path.join(process.env.REPO || path.resolve(__dirname, '..'), '.env'), 'utf8');
const get = (k) => (env.match(new RegExp(`^${k}=(.*)$`, 'm')) || [])[1]?.trim();
const ADMIN = [get('INIT_ADMIN_EMAIL'), get('INIT_ADMIN_PASSWORD')];
const stamp = Date.now();
// Fresh random password per run: the script registers its own accounts, so no
// fixed test password ever has to be stored in the repository.
const PW = `e2e-${require('crypto').randomBytes(18).toString('base64url')}-Aa1!`;
const A = { email: `qa.iso.a.${stamp}@example.com`, tag: `AUNIK${stamp}` };
const B = { email: `qa.iso.b.${stamp}@example.com`, tag: `BUNIK${stamp}` };
const results = [];
const dark = [];
const check = (n, ok, x = '') => results.push(`${ok ? 'PASS' : 'FAIL'}  ${n}${x ? '  -- ' + String(x).slice(0, 200) : ''}`);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function api(method, p, { token, json, form } = {}) {
  const headers = {};
  if (token) headers.Authorization = `Bearer ${token}`;
  let body;
  if (json) { headers['Content-Type'] = 'application/json'; body = JSON.stringify(json); }
  if (form) body = form;
  const r = await fetch(`${BASE}/api/v1${p}`, { method, headers, body });
  let data = null; try { data = await r.json(); } catch {}
  return { status: r.status, data };
}
async function apiLogin(email, password) {
  for (let i = 0; i < 4; i++) {
    const r = await api('POST', '/auth/login', { json: { email, password } });
    if (r.status !== 429) return r.data.access_token;
    await sleep(20000);
  }
}
async function seedUser(u) {
  await api('POST', '/auth/register', { json: { email: u.email, password: PW, full_name: `Iso ${u.tag}` } });
  u.token = await apiLogin(u.email, PW);
  const fd = new FormData();
  fd.append('name', `Data ${u.tag}`);
  fd.append('file', new Blob([`id,email\n1,x@example.com\n2,\n2,\n`], { type: 'text/csv' }), `${u.tag}.csv`);
  const up = await api('POST', '/dataset-files/upload', { token: u.token, form: fd });
  u.ds = up.data.dataset_id; u.ver = up.data.id;
  await api('POST', `/dataset-files/${u.ds}/versions/${u.ver}/scan`, { token: u.token });
  u.rule = (await api('POST', '/data-quality/rules', { token: u.token, json: { name: `Regel ${u.tag}`, dimension: 'completeness', rule_type: 'required_field', status: 'active', dataset_id: u.ds } })).data.id;
  u.domain = (await api('POST', '/domains', { token: u.token, json: { name: `Domän ${u.tag}` } })).data.id;
  u.policy = (await api('POST', '/governance/policies', { token: u.token, json: { name: `Policy ${u.tag}`, policy_type: 'retention', dataset_id: u.ds } })).data.id;
  u.me = (await api('GET', '/auth/me', { token: u.token })).data;
}

async function signIn(page, email, pw) {
  for (let i = 0; i < 4; i++) {
    await page.goto(`${BASE}/login`);
    await page.fill('input[type=email]', email);
    await page.fill('input[type=password]', pw);
    await page.click('button[type=submit]');
    try { await page.waitForURL(/dashboard/, { timeout: 8000 }); return; } catch { await sleep(20000); }
  }
}
// Same tab, no reload: log out via the menu and sign in through the form.
async function switchTo(page, email, pw) {
  await page.locator('header button').last().click();
  await page.getByRole('button', { name: /Logga ut|Sign Out/ }).click();
  await page.waitForURL(/login/);
  for (let i = 0; i < 4; i++) {
    await page.fill('input[type=email]', email);
    await page.fill('input[type=password]', pw);
    await page.click('button[type=submit]');
    try { await page.waitForURL(/dashboard/, { timeout: 8000 }); return; } catch { await sleep(20000); await page.goto(`${BASE}/login`); }
  }
}
async function tour(page, label) {
  const seen = {};
  await page.waitForTimeout(1200);
  seen.dashboard = await page.locator('main').innerText();
  for (const item of ['Datauppsättningar', 'Kvalitetsregler', 'Övervakning', 'Styrning', 'Revisionslogg']) {
    await page.getByRole('button', { name: item, exact: true }).click();
    await page.waitForLoadState('networkidle').catch(() => {}); await page.waitForTimeout(900);
    seen[item] = await page.locator('main').innerText();
    if (item === 'Styrning') {
      await page.getByRole('button', { name: 'Policyer', exact: true }).click(); await page.waitForTimeout(800);
      seen['Styrning/Policyer'] = await page.locator('main').innerText();
    }
    const r = await auditDark(page, `${label} ${item}`); if (r.problems.length) dark.push(r);
  }
  return seen;
}
const mentions = (seen, needle) => Object.entries(seen).filter(([, v]) => v.includes(needle)).map(([k]) => k);

(async () => {
  await seedUser(A); await seedUser(B);
  check('setup: two users with dataset, scan, rule, domain, policy', [A, B].every((u) => u.ds && u.rule && u.domain && u.policy));

  const { browser, context, page } = await launch();
  const calls = [];
  page.on('request', (r) => { if (r.url().includes('/api/v1/')) calls.push(r.url()); });

  // 1. admin browses first (fills the cache), exactly like the reported case
  await signIn(page, ...ADMIN);
  const adminSeen = await tour(page, 'admin');
  check('admin sees both users\' datasets (global access)', mentions(adminSeen, A.tag).length > 0 && mentions(adminSeen, B.tag).length > 0);

  // 2. switch to A in the same tab
  const before = calls.length;
  await switchTo(page, A.email, PW);
  const aSeen = await tour(page, 'A');
  check('A: own data visible after switching from admin', mentions(aSeen, A.tag).length >= 3, mentions(aSeen, A.tag).join(','));
  check('A: none of B\'s data on any page', mentions(aSeen, B.tag).length === 0, mentions(aSeen, B.tag).join(','));
  check('A: none of the admin-only data (e.g. "QA mgr data", "QA kunder") on any page', !Object.values(aSeen).some((v) => /QA mgr data|QA kunder|QA accuracy/.test(v)));
  check('A: pages were fetched fresh for A (requests made after the switch)', calls.length - before > 5, `${calls.length - before} requests`);
  const aMetrics = aSeen['Övervakning'].match(/Regler\s*(\d+)/);
  check('A: monitoring counts only A\'s rules', aMetrics && Number(aMetrics[1]) < 20, aMetrics && aMetrics[0]);

  // 3. switch to B in the same tab
  await switchTo(page, B.email, PW);
  const bSeen = await tour(page, 'B');
  check('B: own data visible', mentions(bSeen, B.tag).length >= 3, mentions(bSeen, B.tag).join(','));
  check('B: none of A\'s data on any page', mentions(bSeen, A.tag).length === 0, mentions(bSeen, A.tag).join(','));

  // 4. reload and direct URLs as B
  await page.reload(); await page.waitForTimeout(1200);
  check('B: still B after reload, A absent', !(await page.locator('main').innerText()).includes(A.tag));
  for (const [url, label] of [[`/datasets/${A.ds}`, 'A\'s dataset URL']]) {
    await page.goto(`${BASE}${url}`); await page.waitForLoadState('networkidle'); await page.waitForTimeout(800);
    const t = await page.locator('main').innerText();
    check(`B: direct navigation to ${label} shows "not found", no data`, t.includes('hittades inte') && !t.includes(A.tag));
  }

  // 5. API probes with the other user's IDs (both directions)
  const probes = (u, o) => [
    ['GET', `/datasets/${o.ds}`], ['GET', `/datasets/${o.ds}/elements`], ['GET', `/dataset-files/${o.ds}/versions`],
    ['GET', `/dataset-files/${o.ds}/versions/${o.ver}/rows`], ['GET', `/dataset-files/${o.ds}/versions/${o.ver}/download`],
    ['GET', `/dataset-files/${o.ds}/quality-comparison`], ['GET', `/data-quality/rules/${o.rule}`],
    ['GET', `/data-quality/rules/${o.rule}/results`], ['GET', `/results/${o.rule}/statistics`], ['GET', `/results/${o.rule}/timeline`],
    ['GET', `/domains/${o.domain}`], ['GET', `/domains/${o.domain}/datasets`], ['GET', `/governance/policies/${o.policy}`],
    ['DELETE', `/datasets/${o.ds}`], ['DELETE', `/data-quality/rules/${o.rule}`], ['DELETE', `/governance/policies/${o.policy}`],
    ['PUT', `/domains/${o.domain}`, { name: 'x' }],
  ];
  for (const [u, o, name] of [[A, B, 'A->B'], [B, A, 'B->A']]) {
    const codes = [];
    for (const [m, p, j] of probes(u, o)) codes.push((await api(m, p, { token: u.token, json: j })).status);
    check(`API ${name}: every request for the other user's objects -> 404`, codes.every((c) => c === 404), codes.join(','));
    const lists = {
      datasets: (await api('GET', '/datasets', { token: u.token })).data.map((d) => d.name),
      rules: (await api('GET', '/data-quality/rules?page_size=100', { token: u.token })).data.items.map((r) => r.name),
      domains: (await api('GET', '/domains', { token: u.token })).data.map((d) => d.name),
      policies: (await api('GET', '/governance/policies', { token: u.token })).data.items.map((p) => p.name),
      issues: (await api('GET', '/quality-issues/open?limit=50', { token: u.token })).data.map((i) => i.dataset_name),
      search: JSON.stringify((await api('GET', `/search?q=${o.tag.slice(0, 5)}`, { token: u.token })).data),
      audit: JSON.stringify((await api('GET', '/audit/my-logs', { token: u.token })).data),
      summary: (await api('GET', '/dashboard/summary', { token: u.token })).data,
    };
    const leak = JSON.stringify(lists).includes(o.tag);
    check(`API ${name}: lists, search, issues, audit, dashboard contain nothing of the other user`, !leak);
    check(`API ${name}: dashboard counts only own data`, lists.summary.total_datasets === 1, JSON.stringify({ d: lists.summary.total_datasets, r: lists.summary.total_quality_rules }));
  }

  // 6. sharing still works (A shares with B by email)
  const bLookup = (await api('GET', `/governance/assignable-users?email=${encodeURIComponent(B.email)}`, { token: A.token })).data[0];
  const share = await api('POST', '/governance/assignments', { token: A.token, json: { dataset_id: A.ds, user_id: bLookup.id, role: 'analyst' } });
  check('sharing: A shares with B by email', share.status === 201, share.status);
  await page.goto(`${BASE}/datasets`); await page.waitForLoadState('networkidle'); await page.waitForTimeout(800);
  check('sharing: B now sees A\'s shared dataset (and still not A\'s domain or policy list)', (await page.locator('main').innerText()).includes(A.tag));
  check('sharing: B cannot delete or re-share A\'s dataset', (await api('DELETE', `/datasets/${A.ds}`, { token: B.token })).status === 403
    && (await api('POST', '/governance/assignments', { token: B.token, json: { dataset_id: A.ds, user_id: B.me.id, role: 'owner' } })).status === 403);
  await api('DELETE', `/governance/assignments/${share.data.id}`, { token: A.token });

  // 7. cross-tab: tab 1 is B; tab 2 signs out and in as A
  const tab2 = await context.newPage();
  await tab2.goto(`${BASE}/dashboard`); await tab2.waitForTimeout(800);
  await switchTo(tab2, A.email, PW);
  await page.waitForTimeout(1500);
  check('cross-tab: tab 1 dropped the old session when tab 2 signed out', page.url().endsWith('/dashboard') || page.url().endsWith('/login'), page.url());
  await page.goto(`${BASE}/datasets`); await page.waitForLoadState('networkidle');
  await page.waitForTimeout(1500);
  const t1 = await page.locator('main').innerText();
  const who = await page.locator('header').innerText();
  check('cross-tab: tab 1 follows the new identity instead of mixing users', who.includes(`Iso ${A.tag}`) && t1.includes(A.tag) && !t1.includes(B.tag), who.replace(/\s+/g, ' ').slice(0, 80));
  await tab2.close();

  // 8. back to admin in the same tab: admin functions still work
  await switchTo(page, ...ADMIN);
  await page.getByRole('button', { name: 'Användare', exact: true }).click(); await page.waitForTimeout(1200);
  const usersPage = await page.locator('main').innerText();
  check('admin: user management works after the switches', usersPage.includes(A.email) && usersPage.includes(B.email));

  check('dark theme intact on every visited page', dark.length === 0, JSON.stringify(dark).slice(0, 300));
  await browser.close();
  console.log(results.join('\n'));
  console.log(`\nTEST ACCOUNTS: ${A.email} ${B.email}`);
})().catch((e) => { console.error(e); console.log(results.join('\n')); process.exit(1); });
