import { describe, it, expect, beforeAll } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import i18next, { type i18n as I18n } from 'i18next';
import { normalizeError, type Translate } from '../errorNormalizer';
import { hasPermission } from '../../auth/permissions';

function loadLocale(lng: string) {
  return JSON.parse(readFileSync(resolve(__dirname, `../../../public/locales/${lng}/translation.json`), 'utf8'));
}

let sv: Translate;
let en: Translate;

beforeAll(async () => {
  const make = async (lng: string): Promise<I18n> => {
    const instance = i18next.createInstance();
    await instance.init({ lng, resources: { [lng]: { translation: loadLocale(lng) } }, interpolation: { escapeValue: false } });
    return instance;
  };
  const svI18n = await make('sv');
  const enI18n = await make('en');
  sv = (key, opts) => svI18n.t(key, opts) as string;
  en = (key, opts) => enI18n.t(key, opts) as string;
});

const httpError = (status: number, data: unknown) => ({ response: { status, data }, request: {}, message: `Request failed with status code ${status}` });

// The exact 422 body the registration endpoint returned when the page crashed
// with "Objects are not valid as a React child (found: object with keys
// {type, loc, msg, input, ctx})".
const REGISTRATION_422 = {
  detail: [
    { type: 'value_error', loc: ['body', 'email'], msg: 'value is not a valid email address: An email address must have an @-sign.', input: 'bad', ctx: { reason: 'An email address must have an @-sign.' } },
    { type: 'string_too_short', loc: ['body', 'password'], msg: 'String should have at least 8 characters', input: 'short', ctx: { min_length: 8 } },
    { type: 'string_too_short', loc: ['body', 'full_name'], msg: 'String should have at least 1 character', input: '', ctx: { min_length: 1 } },
  ],
};

describe('normalizeError', () => {
  it('turns the registration 422 payload into readable Swedish text, never an object', () => {
    const result = normalizeError(httpError(422, REGISTRATION_422), sv);
    expect(typeof result).toBe('string');
    expect(result.split('\n')).toEqual([
      'Ange en giltig e-postadress.',
      'Lösenord måste vara minst 8 tecken.',
      'Fullständigt namn måste fyllas i.',
    ]);
    expect(result).not.toMatch(/String should|\[object Object\]|value_error/);
  });

  it('uses the active language', () => {
    expect(normalizeError(httpError(422, REGISTRATION_422), en).split('\n')[1]).toBe('Password must be at least 8 characters.');
  });

  it('reports missing fields as required', () => {
    const body = { detail: [{ type: 'missing', loc: ['body', 'email'], msg: 'Field required', input: {} }] };
    expect(normalizeError(httpError(422, body), sv)).toBe('E-postadress måste fyllas i.');
  });

  it('maps malformed JSON and unknown fields without leaking internals', () => {
    const body = { detail: [{ type: 'json_invalid', loc: ['body', 0], msg: 'JSON decode error', input: {} }] };
    expect(normalizeError(httpError(422, body), sv)).toBe(sv('apiErrors.badRequest'));
    const unknownField = { detail: [{ type: 'weird', loc: ['body', 'some_field'], msg: 'x' }] };
    expect(normalizeError(httpError(422, unknownField), en)).toBe('Some field is invalid.');
  });

  it('translates known backend messages', () => {
    expect(normalizeError(httpError(400, { detail: 'Email already registered' }), sv)).toBe('E-postadressen är redan registrerad.');
    expect(normalizeError(httpError(401, { detail: 'Invalid email or password' }), sv)).toBe('Fel e-postadress eller lösenord.');
    expect(normalizeError(httpError(403, { detail: 'Insufficient permissions' }), sv)).toBe('Du har inte behörighet att göra detta.');
    expect(normalizeError(httpError(404, { detail: 'Dataset not found' }), sv)).toBe(sv('apiErrors.notFound'));
    expect(normalizeError(httpError(403, { detail: 'Only a super admin can grant the Super Admin role' }), sv)).toBe(sv('apiErrors.superAdminOnly'));
  });

  it('keeps unrecognised but readable backend sentences', () => {
    expect(normalizeError(httpError(400, { detail: 'Unknown column(s): foo' }), sv)).toBe('Unknown column(s): foo');
  });

  it('handles rate limiting from both nginx (HTML body) and the API', () => {
    expect(normalizeError(httpError(429, '<html><body>429 Too Many Requests</body></html>'), sv)).toBe(sv('apiErrors.rateLimited'));
    expect(normalizeError(httpError(429, { detail: 'Too many requests: rate limit 5 per 1 minute exceeded.' }), sv)).toBe(sv('apiErrors.rateLimited'));
  });

  it('never shows server internals or proxy HTML for 5xx', () => {
    expect(normalizeError(httpError(500, { detail: 'psycopg.OperationalError: connection refused' }), sv)).toBe(sv('apiErrors.server'));
    expect(normalizeError(httpError(502, '<html>Bad Gateway</html>'), sv)).toBe(sv('apiErrors.server'));
  });

  it('falls back on the status code when the body is empty or opaque', () => {
    expect(normalizeError(httpError(403, ''), sv)).toBe(sv('apiErrors.forbidden'));
    expect(normalizeError(httpError(404, null), sv)).toBe(sv('apiErrors.notFound'));
    expect(normalizeError(httpError(400, { unexpected: true }), sv)).toBe(sv('apiErrors.badRequest'));
  });

  it('distinguishes network failures and timeouts', () => {
    expect(normalizeError({ request: {}, code: 'ERR_NETWORK', message: 'Network Error' }, sv)).toBe(sv('apiErrors.network'));
    expect(normalizeError({ request: {}, code: 'ECONNABORTED', message: 'timeout' }, sv)).toBe(sv('apiErrors.timeout'));
  });

  it('always returns a non-empty string for any input', () => {
    for (const input of [undefined, null, 42, {}, [], new Error('boom'), 'plain text', { detail: { nested: 1 } }]) {
      const out = normalizeError(input, sv);
      expect(typeof out).toBe('string');
      expect(out.length).toBeGreaterThan(0);
    }
    expect(normalizeError(new Error('boom'), sv)).toBe('boom');
  });

  it('has every apiErrors key in both languages', () => {
    const svKeys = Object.keys(loadLocale('sv').apiErrors).sort();
    const enKeys = Object.keys(loadLocale('en').apiErrors).sort();
    expect(svKeys).toEqual(enKeys);
  });
});

describe('hasPermission', () => {
  it('grants super admins everything and others only their codes', () => {
    expect(hasPermission({ is_super_admin: true, permissions: [] }, 'users:manage')).toBe(true);
    expect(hasPermission({ is_super_admin: false, permissions: ['datasets:view'] }, 'datasets:view')).toBe(true);
    expect(hasPermission({ is_super_admin: false, permissions: ['datasets:view'] }, 'users:manage')).toBe(false);
    expect(hasPermission({ is_super_admin: false }, 'datasets:view')).toBe(false);
    expect(hasPermission(null, 'datasets:view')).toBe(false);
  });
});
