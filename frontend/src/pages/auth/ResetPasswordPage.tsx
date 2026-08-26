import { useState } from 'react';
import { Link as RouterLink, useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Eye, EyeOff } from 'lucide-react';
import { useAuth } from '../../hooks/useAuth';

export function ResetPasswordPage() {
  const { t } = useTranslation();
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token') || '';
  const { resetPassword } = useAuth();
  const [password, setPassword] = useState('');
  const [passwordConfirm, setPasswordConfirm] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showPasswordConfirm, setShowPasswordConfirm] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setMessage('');

    if (!token) {
      setError('Missing or invalid reset link.');
      return;
    }
    if (password !== passwordConfirm) {
      setError(t('auth.passwordsMustMatch'));
      return;
    }

    setIsLoading(true);
    const result = await resetPassword(token, password);
    if (result.success) {
      setMessage(result.message || t('auth.passwordResetSuccess'));
    } else {
      setError(result.error || t('auth.resetFailed'));
    }
    setIsLoading(false);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4 card">
      <h2 className="text-2xl font-bold text-slate-900 mb-6">{t('auth.resetPassword')}</h2>

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
          {error}
        </div>
      )}
      {message && (
        <div className="p-3 bg-green-50 border border-green-200 rounded-lg text-sm text-green-700">
          {message}
        </div>
      )}

      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1">
          {t('auth.newPassword')}
        </label>
        <div className="relative">
          <input
            type={showPassword ? 'text' : 'password'}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="input-base pr-10"
            required
          />
          <button
            type="button"
            onClick={() => setShowPassword(!showPassword)}
            className="absolute right-3 top-1/2 transform -translate-y-1/2 text-slate-500 hover:text-slate-700"
          >
            {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
          </button>
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1">
          {t('auth.confirmPassword')}
        </label>
        <div className="relative">
          <input
            type={showPasswordConfirm ? 'text' : 'password'}
            value={passwordConfirm}
            onChange={(e) => setPasswordConfirm(e.target.value)}
            className="input-base pr-10"
            required
          />
          <button
            type="button"
            onClick={() => setShowPasswordConfirm(!showPasswordConfirm)}
            className="absolute right-3 top-1/2 transform -translate-y-1/2 text-slate-500 hover:text-slate-700"
          >
            {showPasswordConfirm ? <EyeOff size={18} /> : <Eye size={18} />}
          </button>
        </div>
      </div>

      <button type="submit" disabled={isLoading} className="btn-primary w-full">
        {isLoading ? t('common.loading') : t('auth.resetPassword')}
      </button>

      <div className="text-center text-sm">
        <RouterLink to="/login" className="text-primary-600 hover:text-primary-700 font-medium">
          {t('auth.backToLogin')}
        </RouterLink>
      </div>
    </form>
  );
}
