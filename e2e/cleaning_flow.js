// Browser test of the cleaning engine, versioning/restore and executable
// rules, as a new regular user. Usage: BASE=http://localhost:5173 node cleaning_flow.js
const fs = require('fs');
const path = require('path');
require('fs').mkdirSync(path.join(__dirname, 'tmp'), { recursive: true });
const { launch } = require('./lib');
const { auditDark } = require('./darkaudit');

const BASE = process.env.BASE || 'http://localhost:5173';
const stamp = Date.now();
// Fresh random password per run: the script registers its own accounts, so no
// fixed test password ever has to be stored in the repository.
const PW = `e2e-${require('crypto').randomBytes(18).toString('base64url')}-Aa1!`;
const EMAIL = `qa.clean.${stamp}@example.com`;
const results = [];
const dark = [];
const check = (n, ok, x = '') => results.push(`${ok ? 'PASS' : 'FAIL'}  ${n}${x ? '  -- ' + String(x).slice(0, 220) : ''}`);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// id,namn,stad,datum,belopp  - planted problems:
// row 3 duplicates row 2 by id; "sthlm"/"gbg" categories; ambiguous 01/02/2024;
// decimal-comma amounts; a zero-width space in row 1's name.
const CSV = 'id,namn,stad,datum,belopp\n1,Anna​,sthlm,2024-03-05,"1,5"\n2,Bo,gbg,31/12/2024,"2,25"\n2,Bo,gbg,31/12/2024,"2,25"\n4,Cia,Malmö,01/02/2024,abc\n';
const file = path.join(__dirname, 'tmp', `clean_${stamp}.csv`);
fs.writeFileSync(file, CSV);

(async () => {
  await fetch(`${BASE}/api/v1/auth/register`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email: EMAIL, password: PW, full_name: 'Clean Test' }) });
  const { browser, page, log } = await launch();
  for (let i = 0; i < 4; i++) {
    await page.goto(`${BASE}/login`);
    await page.fill('input[type=email]', EMAIL); await page.fill('input[type=password]', PW); await page.click('button[type=submit]');
    try { await page.waitForURL(/dashboard/, { timeout: 8000 }); break; } catch { await sleep(20000); }
  }
  await page.goto(`${BASE}/datasets?upload=1`); await page.waitForTimeout(800);
  await page.locator('form input:not([type=file])').first().fill(`Rensning ${stamp}`);
  await page.setInputFiles('input[type=file]', file);
  await page.locator('form button[type=submit]').click();
  await page.waitForURL(/\/datasets\/[0-9a-f-]{36}/, { timeout: 30000 });
  const dsUrl = page.url();
  await page.waitForLoadState('networkidle');

  // ---- Rensa: build four operations through the UI ----
  await page.getByRole('button', { name: /^Rensa/ }).click(); await page.waitForTimeout(800);
  const opSelects = () => page.getByRole('combobox', { name: 'Åtgärd' });
  const opBox = (i) => page.locator('div.p-3.bg-slate-50').nth(i);
  // 1: remove invisible characters (default "all columns")
  await opSelects().nth(0).selectOption('remove_control_characters');
  // 2: normalize dates on "datum", day order unknown
  await page.getByRole('button', { name: 'Lägg till åtgärd' }).click();
  await opSelects().nth(1).selectOption('normalize_dates');
  await opBox(1).getByRole('button', { name: 'datum', exact: true }).click();
  // 3: convert "belopp" to decimal with decimal comma
  await page.getByRole('button', { name: 'Lägg till åtgärd' }).click();
  await opSelects().nth(2).selectOption('convert_type');
  await opBox(2).getByRole('button', { name: 'belopp', exact: true }).click();
  await opBox(2).locator('select').nth(1).selectOption('decimal');
  await opBox(2).locator('select').nth(2).selectOption(',');
  // 4: map categories
  await page.getByRole('button', { name: 'Lägg till åtgärd' }).click();
  await opSelects().nth(3).selectOption('map_values');
  await opBox(3).getByRole('button', { name: 'stad', exact: true }).click();
  await opBox(3).locator('textarea').fill('sthlm = Stockholm\ngbg = Göteborg');
  // 5: remove duplicates compared on "id"
  await page.getByRole('button', { name: 'Lägg till åtgärd' }).click();
  await opSelects().nth(4).selectOption('remove_duplicate_rows');
  await opBox(4).getByRole('button', { name: 'id', exact: true }).click();

  await page.getByRole('button', { name: 'Förhandsgranska' }).click(); await page.waitForTimeout(2500);
  let t = (await page.locator('main').innerText()).replace(/\s+/g, ' ');
  const num = (label) => { const m = t.match(new RegExp(`${label}\\s*(\\d+)`)); return m ? Number(m[1]) : null; };
  check('preview: 1 row removed (duplicate id)', num('Borttagna rader') === 1, t.slice(0, 300));
  check('preview: ambiguous date 01/02/2024 skipped and reported', /01\/02\/2024.*tvetydigt datum/.test(t));
  check('preview: invalid amount "abc" reported, not converted', /abc.*ogiltigt värde/.test(t));
  check('preview: quality score before → after shown', /Kvalitetspoäng före → efter\s*\d+(\.\d)?% → \d+(\.\d)?%/.test(t), (t.match(/Kvalitetspoäng före → efter[^A-Z]*/) || [''])[0]);
  check('preview: removed row shown by its original row number', /\b3\b[^\n]*Raden tas bort/.test(t));
  check('preview: score note shown because rows are removed', t.includes('Att ta bort rader kan höja poängen'));
  await dark.push(...[(await auditDark(page, 'clean preview'))].filter((r) => r.problems.length));

  // editing invalidates the preview
  await opBox(3).locator('textarea').fill('sthlm = Stockholm');
  await page.waitForTimeout(300);
  const applyBtn = page.getByRole('button', { name: 'Tillämpa (skapar ny version)' });
  check('editing an operation disables apply until previewed again', await applyBtn.isDisabled() && (await page.locator('main').innerText()).includes('förhandsgranska igen'));
  await opBox(3).locator('textarea').fill('sthlm = Stockholm\ngbg = Göteborg');
  await page.getByRole('button', { name: 'Förhandsgranska' }).click(); await page.waitForTimeout(2500);

  // apply -> confirmation because rows are removed
  await applyBtn.click(); await page.waitForTimeout(500);
  check('confirmation required before removing rows', (await page.locator('main').innerText()).includes('Rader kommer att tas bort'));
  await dark.push(...[(await auditDark(page, 'confirm removal'))].filter((r) => r.problems.length));
  await page.locator('div.fixed').getByRole('button', { name: 'Tillämpa (skapar ny version)' }).click();
  await page.waitForTimeout(3000);

  // versions: history + download v2
  await page.getByRole('button', { name: /^Versioner/ }).click(); await page.waitForTimeout(1000);
  t = (await page.locator('main').innerText()).replace(/\s+/g, ' ');
  check('history: v2 lists the operations that produced it', /v2.*Ta bort osynliga tecken → Normalisera datumformat → Konvertera datatyp → Standardisera kategorivärden → Ta bort dubblettrader/.test(t), t.slice(0, 400));
  const rows = page.locator('tbody tr');
  const [dl] = await Promise.all([page.waitForEvent('download'), rows.first().getByRole('button', { name: 'Ladda ner' }).click()]);
  const body = fs.readFileSync(await dl.path(), 'utf8');
  const expected = 'id,namn,stad,datum,belopp\n1,Anna,Stockholm,2024-03-05,1.5\n2,Bo,Göteborg,2024-12-31,2.25\n4,Cia,Malmö,01/02/2024,abc\n';
  check('download: cleaned file exactly as expected (ambiguous date and invalid amount untouched)', body.replace(/\r/g, '') === expected, JSON.stringify(body));
  await dark.push(...[(await auditDark(page, 'versions'))].filter((r) => r.problems.length));

  // restore v1
  await rows.last().getByRole('button', { name: 'Återställ version' }).click(); await page.waitForTimeout(400);
  await page.locator('div.fixed').getByRole('button', { name: 'Återställ version' }).click(); await page.waitForTimeout(2500);
  await page.getByRole('button', { name: /^Versioner/ }).click(); await page.waitForTimeout(800);
  t = (await page.locator('main').innerText()).replace(/\s+/g, ' ');
  check('restore: v3 created as "Återställd från v1", v1 and v2 kept', /v3.*Återställd från v1/.test(t) && /v2/.test(t) && /v1/.test(t));

  // ---- executable rule through the UI ----
  await page.goto(`${BASE}/data-quality/rules`); await page.waitForLoadState('networkidle');
  await page.getByRole('button', { name: 'Lägg till' }).click(); await page.waitForTimeout(400);
  await page.fill('#rule-name', `Belopp 0-2 ${stamp}`);
  await page.selectOption('#rule-type', 'numeric_range');
  await page.selectOption('#rule-dataset', { label: `Rensning ${stamp}` });
  await page.waitForTimeout(800);
  await page.selectOption('#rule-column', 'belopp');
  await page.fill('#rule-min', '0'); await page.fill('#rule-max', '2');
  await dark.push(...[(await auditDark(page, 'rule dialog'))].filter((r) => r.problems.length));
  await page.locator('form button[type=submit]').click(); await page.waitForTimeout(1200);
  const ruleRow = page.locator('tr', { hasText: `Belopp 0-2 ${stamp}` });
  check('rule: executable rule created, shown as "Inte körd ännu"', (await ruleRow.innerText()).includes('Inte körd ännu'));
  await ruleRow.getByRole('button', { name: 'Kör regeln' }).click(); await page.waitForTimeout(2000);
  t = (await page.locator('main').innerText()).replace(/\s+/g, ' ');
  // latest version is v3 = original file: values "1,5", "2,25", "2,25", "abc" -> with "." separator all fail as not numbers
  check('rule: run reports failures with row numbers', /underkändes\. Första raderna: 1, 2, 3, 4/.test(t), (t.match(/"Belopp[^.]*\.[^.]*\./) || [''])[0]);
  check('rule: table shows last result', (await ruleRow.innerText()).includes('4 av 4 underkända'));
  await page.getByRole('button', { name: 'Lägg till' }).click(); await page.waitForTimeout(400);
  await page.fill('#rule-name', `Dokumentation ${stamp}`);
  await page.selectOption('#rule-type', 'other');
  await page.fill('input[placeholder^="Beskriv regeltypen"]', 'manuell granskning');
  await page.locator('form button[type=submit]').click(); await page.waitForTimeout(1200);
  const docRow = page.locator('tr', { hasText: `Dokumentation ${stamp}` });
  check('rule: documentation-only rule says so and has no run button', (await docRow.innerText()).includes('Endast definition') && (await docRow.getByRole('button', { name: 'Kör regeln' }).count()) === 0);
  await dark.push(...[(await auditDark(page, 'rules list'))].filter((r) => r.problems.length));

  check('dark theme intact on every audited view', dark.length === 0, JSON.stringify(dark).slice(0, 300));
  const errors = log.pageErrors;
  check('no page errors', errors.length === 0, JSON.stringify(errors));
  await browser.close();
  console.log(results.join('\n'));
  console.log(`ACCOUNT: ${EMAIL}`);
})().catch((e) => { console.error(e); console.log(results.join('\n')); process.exit(1); });
