import { useEffect, useState } from 'react';
import { Link as RouterLink, useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { CheckCircle, XCircle, Loader } from 'lucide-react';
import { useAuth } from '../../hooks/useAuth';

export function VerifyEmailPage() {
  const { t } = useTranslation();
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token') || '';
  const { verifyEmail } = useAuth();
  const [status, setStatus] = useState<'verifying' | 'success' | 'error'>('verifying');
  const [error, setError] = useState('');

  useEffect(() => {
    if (!token) {
      setStatus('error');
      setError('Missing or invalid verification link.');
      return;
    }
    let cancelled = false;
    verifyEmail(token).then((result) => {
      if (cancelled) return;
      if (result.success) {
        setStatus('success');
      } else {
        setStatus('error');
        setError(result.error || t('auth.verificationFailed'));
      }
    });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  return (
    <div className="card space-y-4 text-center">
      <h2 className="text-2xl font-bold text-slate-900">{t('auth.verifyEmail')}</h2>

      {status === 'verifying' && (
        <div className="flex flex-col items-center gap-3 py-6">
          <Loader className="w-8 h-8 text-primary-600 animate-spin" />
          <p className="text-sm text-slate-600">{t('common.loading')}</p>
        </div>
      )}

      {status === 'success' && (
        <div className="flex flex-col items-center gap-3 py-6">
          <CheckCircle className="w-10 h-10 text-green-600" />
          <p className="text-sm text-slate-700">{t('auth.emailVerified')}</p>
        </div>
      )}

      {status === 'error' && (
        <div className="flex flex-col items-center gap-3 py-6">
          <XCircle className="w-10 h-10 text-red-600" />
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      <RouterLink to="/login" className="text-primary-600 hover:text-primary-700 font-medium text-sm">
        {t('auth.backToLogin')}
      </RouterLink>
    </div>
  );
}
