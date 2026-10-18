// Call EVERY GET endpoint in the OpenAPI schema as user B, with path
// parameters set to user A's object IDs, and check nothing of A leaks.
// Usage: node endpoint_sweep.js
const API = 'http://127.0.0.1:8000';
const stamp = Date.now();
const PW = '[REDACTED-DEV-CREDENTIAL]';
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function call(method, path, token, body, form) {
  const headers = token ? { Authorization: `Bearer ${token}` } : {};
  if (body) headers['Content-Type'] = 'application/json';
  const r = await fetch(API + path, { method, headers, body: form || (body ? JSON.stringify(body) : undefined) });
  const text = await r.text();
  return { status: r.status, text };
}
async function user(tag) {
  const email = `qa.sweep.${tag.toLowerCase()}.${stamp}@example.com`;
  await call('POST', '/api/v1/auth/register', null, { email, password: PW, full_name: `Sweep ${tag}` });
  let tok;
  for (let i = 0; i < 4 && !tok; i++) {
    const r = await call('POST', '/api/v1/auth/login', null, { email, password: PW });
    if (r.status === 429) { await sleep(20000); continue; }
    tok = JSON.parse(r.text).access_token;
  }
  return { email, tok, tag };
}

(async () => {
  const A = await user(`SWEEPA${stamp}`);
  const B = await user(`SWEEPB${stamp}`);
  // A creates one of everything.
  const fd = new FormData();
  fd.append('name', `DS ${A.tag}`);
  fd.append('file', new Blob([`id,email\n1,a@x.se\n1,\n`], { type: 'text/csv' }), 'a.csv');
  const up = JSON.parse((await call('POST', '/api/v1/dataset-files/upload', A.tok, null, fd)).text);
  await call('POST', `/api/v1/dataset-files/${up.dataset_id}/versions/${up.id}/scan`, A.tok);
  const rule = JSON.parse((await call('POST', '/api/v1/data-quality/rules', A.tok, { name: `Rule ${A.tag}`, dimension: 'completeness', rule_type: 'x', status: 'active', dataset_id: up.dataset_id })).text);
  const dom = JSON.parse((await call('POST', '/api/v1/domains', A.tok, { name: `Dom ${A.tag}` })).text);
  const pol = JSON.parse((await call('POST', '/api/v1/governance/policies', A.tok, { name: `Pol ${A.tag}`, policy_type: 'retention', dataset_id: up.dataset_id })).text);
  const els = JSON.parse((await call('GET', `/api/v1/datasets/${up.dataset_id}/elements`, A.tok)).text);
  const meA = JSON.parse((await call('GET', '/api/v1/auth/me', A.tok)).text);
  const ids = {
    dataset_id: up.dataset_id, version_id: up.id, rule_id: rule.id, domain_id: dom.id, policy_id: pol.id,
    element_id: els[0]?.id, user_id: meA.id, dimension: 'completeness', log_id: '00000000-0000-0000-0000-000000000000',
    department_id: '00000000-0000-0000-0000-000000000000', role_id: '00000000-0000-0000-0000-000000000000',
    assignment_id: '00000000-0000-0000-0000-000000000000',
  };
  const markers = [A.tag, up.dataset_id, rule.id, dom.id, pol.id, A.email];

  const spec = JSON.parse((await call('GET', '/openapi.json')).text);
  const rows = [];
  for (const [path, ops] of Object.entries(spec.paths)) {
    if (!ops.get) continue;
    let url = path.replace(/\{(\w+)\}/g, (_, k) => ids[k] ?? 'x');
    // Query params that select a dataset/rule: point them at A's objects too.
    const qp = (ops.get.parameters || []).filter((p) => p.in === 'query').map((p) => p.name);
    const q = [];
    if (qp.includes('dataset_id')) q.push(`dataset_id=${ids.dataset_id}`);
    if (qp.includes('rule_id')) q.push(`rule_id=${ids.rule_id}`);
    if (qp.includes('q')) q.push(`q=${A.tag.slice(0, 6)}`);
    if (qp.includes('email')) q.push(`email=${encodeURIComponent(A.email)}`);
    if (q.length) url += `?${q.join('&')}`;
    const r = await call('GET', url, B.tok);
    const leaked = markers.filter((m) => r.text.includes(m));
    rows.push({ url: url.replace(/[0-9a-f-]{36}/g, ':id'), status: r.status, leaked });
  }
  // The exact-email sharing lookup is meant to resolve an address you already know.
  const allowed = (r) => r.url.startsWith('/api/v1/governance/assignable-users');
  const bad = rows.filter((r) => r.leaked.length && !allowed(r));
  for (const r of rows) console.log(`${r.leaked.length && !allowed(r) ? 'LEAK' : 'ok  '} ${String(r.status).padEnd(4)} ${r.url}${r.leaked.length ? '  contains: ' + r.leaked.map((m) => (m === A.email ? 'A.email' : m.length > 30 ? 'A-object-id' : 'A-name')).join(',') : ''}`);
  console.log(`\nchecked ${rows.length} GET endpoints as user B against user A's objects: ${bad.length} leaks`);
  console.log(`ACCOUNTS: ${A.email} ${B.email}`);
})().catch((e) => { console.error(e); process.exit(1); });
