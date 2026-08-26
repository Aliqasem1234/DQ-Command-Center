import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import { AlertCircle, Eye, EyeOff, Loader } from 'lucide-react';
import { useAuth } from '../../hooks/useAuth';

interface LoginError {
  field?: string;
  message: string;
}

export function LoginPageModern() {
  const { t } = useTranslation();
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<LoginError | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    const result = await login({ email, password });
    if (!result.success) {
      setError({ message: result.error || t('auth.loginFailed') });
    }
    setLoading(false);
  };

  return (
    <div className="card-lg !rounded-2xl !shadow-lg">
      <h2 className="text-xl font-bold text-slate-900 mb-6">{t('auth.login')}</h2>
      <form onSubmit={handleSubmit} className="space-y-5">
        {error && (
          <div className="alert alert-error">
            <AlertCircle className="w-5 h-5 flex-shrink-0" />
            <p className="text-sm font-medium">{error.message}</p>
          </div>
        )}

        {/* Email Field */}
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-2">
            {t('auth.email')}
          </label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            className="input-base"
            placeholder={t('auth.emailPlaceholder')}
            disabled={loading}
          />
        </div>

        {/* Password Field */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="block text-sm font-medium text-slate-700">
              {t('auth.password')}
            </label>
            <Link to="/forgot-password" className="text-sm text-primary-600 hover:text-primary-700">
              {t('auth.forgotShort')}
            </Link>
          </div>
          <div className="relative">
            <input
              type={showPassword ? 'text' : 'password'}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="input-base pr-10"
              placeholder="••••••••"
              disabled={loading}
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
              disabled={loading}
              aria-label={showPassword ? t('auth.hidePassword') : t('auth.showPassword')}
            >
              {showPassword ? (
                <EyeOff className="w-4 h-4" />
              ) : (
                <Eye className="w-4 h-4" />
              )}
            </button>
          </div>
        </div>

        {/* Submit Button */}
        <button
          type="submit"
          disabled={loading}
          className="w-full btn-primary flex items-center justify-center gap-2 py-3"
        >
          {loading ? (
            <>
              <Loader className="w-4 h-4 animate-spin" />
              {t('auth.signingIn')}
            </>
          ) : (
            t('auth.login')
          )}
        </button>
      </form>

      {/* Register Link */}
      <div className="mt-6 pt-6 border-t border-slate-100 dark:border-slate-800 text-center">
        <p className="text-slate-500 text-sm">
          {t('auth.noAccount')}{' '}
          <Link to="/register" className="text-primary-600 hover:text-primary-700 font-medium">
            {t('auth.registerHere')}
          </Link>
        </p>
      </div>

      {/* Footer */}
      <p className="text-center text-xs text-slate-400 mt-6 -mb-2">
        {t('app.copyright', { year: new Date().getFullYear() })}
      </p>
    </div>
  );
}
