import { useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../../hooks/useAuth';

export function ForgotPasswordPage() {
  const { t } = useTranslation();
  const { forgotPassword } = useAuth();
  const [email, setEmail] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setMessage('');
    setIsLoading(true);
    const result = await forgotPassword(email);
    if (result.success) {
      setMessage(result.message || t('auth.resetEmailSent'));
    } else {
      setError(result.error || t('auth.resetFailed'));
    }
    setIsLoading(false);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-5 card-lg">
      <h2 className="text-xl font-bold text-slate-900 mb-2">{t('auth.forgotPassword')}</h2>
      <p className="text-sm text-slate-600 mb-6">{t('auth.enterEmailForReset')}</p>

      {message && (
        <div className="alert alert-success text-sm">
          {message}
        </div>
      )}
      {error && (
        <div className="alert alert-error text-sm">
          {error}
        </div>
      )}

      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1">
          {t('auth.email')}
        </label>
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="input-base"
          required
        />
      </div>

      <button type="submit" disabled={isLoading} className="btn-primary w-full">
        {isLoading ? t('common.loading') : t('auth.sendReset')}
      </button>

      <div className="text-center text-sm">
        <RouterLink to="/login" className="text-primary-600 hover:text-primary-700 font-medium">
          {t('auth.backToLogin')}
        </RouterLink>
      </div>
    </form>
  );
}
