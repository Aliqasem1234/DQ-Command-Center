import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useAuthStore } from '../../store/authStore';
import { authService } from '../../services/authService';
import { getErrorMessage } from '../../services/api';

export function ProfilePage() {
  const { t } = useTranslation();
  const { user, setUser } = useAuthStore();
  const [isEditing, setIsEditing] = useState(false);
  const [fullName, setFullName] = useState(user?.full_name || '');
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState<string | null>(null);

  const startEditing = () => {
    setFullName(user?.full_name || '');
    setError(null);
    setIsEditing(true);
  };

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    try {
      const updated = await authService.updateProfile(fullName);
      setUser(updated);
      setMessage(t('common.saved'));
      setIsEditing(false);
      setTimeout(() => setMessage(''), 3000);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="max-w-2xl">
      <h1 className="text-2xl font-bold tracking-tight text-slate-900 mb-6">{t('nav.myProfile')}</h1>

      {message && (
        <div className="mb-4 p-4 bg-green-50 border border-green-200 rounded-lg text-green-700">
          {message}
        </div>
      )}
      {error && (
        <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
          {error}
        </div>
      )}

      <div className="card-lg">
        <div className="mb-6">
          <h2 className="text-xl font-semibold text-slate-900 mb-4">{t('auth.userInfo')}</h2>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                {t('auth.fullName')}
              </label>
              <input
                type="text"
                value={isEditing ? fullName : user?.full_name || ''}
                onChange={(e) => setFullName(e.target.value)}
                disabled={!isEditing}
                className={`input-base ${!isEditing ? 'bg-slate-50 cursor-not-allowed' : ''}`}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                {t('auth.email')}
              </label>
              <input
                type="email"
                value={user?.email || ''}
                disabled
                className="input-base bg-slate-50 cursor-not-allowed"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                {t('auth.role')}
              </label>
              <input
                type="text"
                value={user?.is_super_admin ? t('profile.superAdmin') : user?.roles?.[0] || '-'}
                disabled
                className="input-base bg-slate-50 cursor-not-allowed"
              />
            </div>
          </div>
        </div>

        <div className="flex gap-3 pt-4 border-t border-slate-200">
          {!isEditing ? (
            <button onClick={startEditing} className="btn-primary">
              {t('common.edit')}
            </button>
          ) : (
            <>
              <button onClick={handleSave} disabled={saving} className="btn-primary">
                {saving ? t('common.loading') : t('common.save')}
              </button>
              <button
                onClick={() => setIsEditing(false)}
                disabled={saving}
                className="btn-secondary"
              >
                {t('common.cancel')}
              </button>
            </>
          )}
        </div>
      </div>

    </div>
  );
}

export function ChangePasswordCard() {
  const { t } = useTranslation();
  const [current, setCurrent] = useState('');
  const [next, setNext] = useState('');
  const [confirm, setConfirm] = useState('');
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setMessage('');
    if (next !== confirm) {
      setError(t('auth.passwordsMustMatch'));
      return;
    }
    setSaving(true);
    try {
      await authService.changePassword({ current_password: current, new_password: next });
      setMessage(t('auth.passwordChanged'));
      setCurrent('');
      setNext('');
      setConfirm('');
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="card-lg space-y-4" aria-labelledby="change-password-heading">
      <h2 id="change-password-heading" className="text-xl font-semibold text-slate-900">{t('auth.changePassword')}</h2>
      {message && <div className="alert alert-success text-sm" role="status">{message}</div>}
      {error && <div className="alert alert-error text-sm whitespace-pre-line" role="alert">{error}</div>}
      <div>
        <label htmlFor="current-password" className="block text-sm font-medium text-slate-700 mb-1">{t('auth.currentPassword')}</label>
        <input id="current-password" type="password" className="input-base" autoComplete="current-password"
          value={current} onChange={(e) => setCurrent(e.target.value)} required />
      </div>
      <div>
        <label htmlFor="new-password" className="block text-sm font-medium text-slate-700 mb-1">{t('auth.newPassword')}</label>
        <input id="new-password" type="password" className="input-base" autoComplete="new-password" minLength={8} maxLength={128}
          value={next} onChange={(e) => setNext(e.target.value)} required />
      </div>
      <div>
        <label htmlFor="confirm-new-password" className="block text-sm font-medium text-slate-700 mb-1">{t('auth.confirmPassword')}</label>
        <input id="confirm-new-password" type="password" className="input-base" autoComplete="new-password" minLength={8} maxLength={128}
          value={confirm} onChange={(e) => setConfirm(e.target.value)} required />
      </div>
      <div className="pt-2">
        <button type="submit" disabled={saving} className="btn-primary">
          {saving ? t('common.loading') : t('auth.changePassword')}
        </button>
      </div>
    </form>
  );
}
