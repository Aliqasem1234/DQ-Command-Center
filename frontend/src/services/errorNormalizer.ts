/**
 * Turns any thrown value - an Axios error carrying a FastAPI response, a
 * network failure, a plain Error - into one readable, translated sentence.
 *
 * FastAPI answers validation failures (422) with `detail` as an *array of
 * objects* ({type, loc, msg, input, ctx}). Passing that straight to JSX
 * crashed the registration page with "Objects are not valid as a React
 * child", so nothing from a response body is ever returned unprocessed: the
 * result is always a string.
 */
import i18next, { type TFunction } from 'i18next';

export type Translate = (key: string, options?: Record<string, unknown>) => string;

interface FastApiValidationItem {
  type?: string;
  loc?: (string | number)[];
  msg?: string;
  ctx?: Record<string, unknown>;
}

interface HttpLikeError {
  response?: { status?: number; data?: unknown };
  request?: unknown;
  code?: string;
  message?: string;
}

const defaultTranslate: Translate = (key, options) =>
  (i18next.t as TFunction)(key, options as never) as unknown as string;

// Fixed backend messages -> translation keys. Backend text stays English
// (it is also the API contract); the UI shows it in the user's language.
const KNOWN_DETAILS: Record<string, string> = {
  'email already registered': 'apiErrors.emailTaken',
  'email already in use': 'apiErrors.emailTaken',
  'username already taken': 'apiErrors.usernameTaken',
  'invalid email or password': 'apiErrors.invalidCredentials',
  'account is locked. try again later.': 'apiErrors.accountLocked',
  'account is deactivated': 'apiErrors.accountDeactivated',
  'invalid or expired reset token': 'apiErrors.invalidResetToken',
  'invalid or expired verification token': 'apiErrors.invalidVerificationToken',
  'invalid or expired refresh token': 'apiErrors.unauthorized',
  'invalid or expired token': 'apiErrors.unauthorized',
  'not authenticated': 'apiErrors.unauthorized',
  'current password is incorrect': 'apiErrors.currentPasswordIncorrect',
  'insufficient permissions': 'apiErrors.forbidden',
  'cannot deactivate yourself': 'apiErrors.cannotDeactivateSelf',
  'cannot delete system roles': 'apiErrors.systemRoleLocked',
  'cannot modify system roles': 'apiErrors.systemRoleLocked',
  'role name already exists': 'apiErrors.nameTaken',
  'role with this name already exists': 'apiErrors.nameTaken',
  'department with this name already exists': 'apiErrors.nameTaken',
  'an internal server error occurred': 'apiErrors.server',
};

const DETAIL_PATTERNS: Array<[RegExp, string]> = [
  [/^only a super admin can/i, 'apiErrors.superAdminOnly'],
  [/^too many requests/i, 'apiErrors.rateLimited'],
  [/^a dataset named .* already exists/i, 'apiErrors.datasetNameTaken'],
  [/exceeds the .*upload limit/i, 'apiErrors.fileTooLarge'],
  [/^unsupported file/i, 'apiErrors.unsupportedFile'],
  [/^could not process file/i, 'apiErrors.fileProcessing'],
  [/ not found$/i, 'apiErrors.notFound'],
];

function translateDetail(detail: string, t: Translate): string {
  const key = KNOWN_DETAILS[detail.trim().toLowerCase()];
  if (key) return t(key);
  for (const [pattern, patternKey] of DETAIL_PATTERNS) {
    if (pattern.test(detail)) return t(patternKey);
  }
  // An unrecognised but human-readable backend sentence (e.g. a specific
  // cleaning-operation error) is more useful shown than hidden.
  return detail;
}

function fieldLabel(loc: FastApiValidationItem['loc'], t: Translate): string | null {
  if (!Array.isArray(loc)) return null;
  // loc is ["body", "<field>", ...] - the last string segment is the field.
  const field = [...loc].reverse().find((part) => typeof part === 'string' && part !== 'body');
  if (typeof field !== 'string') return null;
  const label = t(`fields.${field}`, { defaultValue: '' });
  return label || field.replace(/_/g, ' ').replace(/^\w/, (c) => c.toUpperCase());
}

function translateValidationItem(item: FastApiValidationItem, t: Translate): string {
  const field = fieldLabel(item.loc, t);
  const ctx = item.ctx ?? {};
  const type = item.type ?? '';

  if (type === 'json_invalid') return t('apiErrors.badRequest');
  if (field === null) return t('apiErrors.invalidInput');

  const isEmailField = Array.isArray(item.loc) && item.loc.includes('email');
  if (isEmailField && type !== 'missing') return t('apiErrors.invalidEmail');

  switch (type) {
    case 'missing':
      return t('apiErrors.fieldRequired', { field });
    case 'string_too_short':
      return Number(ctx.min_length) <= 1
        ? t('apiErrors.fieldRequired', { field })
        : t('apiErrors.fieldTooShort', { field, min: ctx.min_length });
    case 'string_too_long':
      return t('apiErrors.fieldTooLong', { field, max: ctx.max_length });
    default:
      return t('apiErrors.fieldInvalid', { field });
  }
}

function fromResponseBody(data: unknown, t: Translate): string | null {
  if (typeof data === 'string') {
    // An HTML error page (e.g. from the proxy) is never shown to the user.
    return data.trim() && !data.trim().startsWith('<') ? translateDetail(data, t) : null;
  }
  if (!data || typeof data !== 'object') return null;
  const { detail } = data as { detail?: unknown };

  if (typeof detail === 'string' && detail.trim()) return translateDetail(detail, t);
  if (Array.isArray(detail) && detail.length > 0) {
    const messages = detail
      .filter((d): d is FastApiValidationItem => !!d && typeof d === 'object')
      .map((d) => translateValidationItem(d, t));
    // One message per line, without repeats (e.g. several issues on a field).
    return [...new Set(messages)].join('\n') || t('apiErrors.invalidInput');
  }
  if (detail && typeof detail === 'object' && typeof (detail as { msg?: unknown }).msg === 'string') {
    return translateDetail((detail as { msg: string }).msg, t);
  }
  return null;
}

function fromStatus(status: number, t: Translate): string {
  if (status === 401) return t('apiErrors.unauthorized');
  if (status === 403) return t('apiErrors.forbidden');
  if (status === 404) return t('apiErrors.notFound');
  if (status === 408) return t('apiErrors.timeout');
  if (status === 422) return t('apiErrors.invalidInput');
  if (status === 429) return t('apiErrors.rateLimited');
  if (status >= 500) return t('apiErrors.server');
  return t('apiErrors.badRequest');
}

export function normalizeError(error: unknown, t: Translate = defaultTranslate): string {
  if (error && typeof error === 'object') {
    const err = error as HttpLikeError;
    const status = err.response?.status;

    if (err.response) {
      // Rate limits and server failures read the same whatever the body says
      // (and a 5xx body may carry internals not meant for users).
      if (status === 429) return t('apiErrors.rateLimited');
      if (status !== undefined && status >= 500) return t('apiErrors.server');
      return fromResponseBody(err.response.data, t) ?? fromStatus(status ?? 0, t);
    }
    if (err.code === 'ECONNABORTED' || err.code === 'ETIMEDOUT') return t('apiErrors.timeout');
    if (err.request !== undefined || err.code === 'ERR_NETWORK') return t('apiErrors.network');
  }

  if (error instanceof Error && error.message) return error.message;
  if (typeof error === 'string' && error.trim()) return error;
  return t('errors.unexpectedError');
}
