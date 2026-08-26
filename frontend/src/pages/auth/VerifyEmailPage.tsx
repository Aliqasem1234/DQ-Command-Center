import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

export function VerifyEmailPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [code, setCode] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    // Auto-redirect if no verification needed
    const timer = setTimeout(() => navigate('/login'), 3000);
    return () => clearTimeout(timer);
  }, [navigate]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      // Email verification would call API
      navigate('/login');
    } catch (err: any) {
      setError(err.message || t('auth.verificationFailed'));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4 card">
      <h2 className="text-2xl font-bold text-slate-900 mb-2">{t('auth.verifyEmail')}</h2>
      <p className="text-sm text-slate-600 mb-6">{t('auth.enterVerificationCode')}</p>

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
          {error}
        </div>
      )}

      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1">
          {t('auth.verificationCode')}
        </label>
        <input
          type="text"
          value={code}
          onChange={(e) => setCode(e.target.value)}
          className="input-base text-center text-lg tracking-widest"
          placeholder="000000"
          maxLength={6}
          required
        />
      </div>

      <button type="submit" disabled={isLoading} className="btn-primary w-full">
        {isLoading ? t('common.loading') : t('auth.verify')}
      </button>

      <p className="text-xs text-slate-500 text-center">{t('auth.redirecting')}</p>
    </form>
  );
}
