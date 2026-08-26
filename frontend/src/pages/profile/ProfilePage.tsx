import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useAuthStore } from '../../store/authStore';

export function ProfilePage() {
  const { t } = useTranslation();
  const { user } = useAuthStore();
  const [isEditing, setIsEditing] = useState(false);
  const [message, setMessage] = useState('');

  const handleSave = () => {
    setMessage(t('common.saved'));
    setIsEditing(false);
    setTimeout(() => setMessage(''), 3000);
  };

  return (
    <div className="max-w-2xl">
      <h1 className="text-3xl font-bold text-slate-900 mb-6">{t('nav.settings')}</h1>

      {message && (
        <div className="mb-4 p-4 bg-green-50 border border-green-200 rounded-lg text-green-700">
          {message}
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
                value={user?.full_name || ''}
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
                value={user?.roles?.[0] || '-'}
                disabled
                className="input-base bg-slate-50 cursor-not-allowed"
              />
            </div>
          </div>
        </div>

        <div className="flex gap-3 pt-4 border-t border-slate-200">
          {!isEditing ? (
            <button
              onClick={() => setIsEditing(true)}
              className="btn-primary"
            >
              {t('common.edit')}
            </button>
          ) : (
            <>
              <button
                onClick={handleSave}
                className="btn-primary"
              >
                {t('common.save')}
              </button>
              <button
                onClick={() => setIsEditing(false)}
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
