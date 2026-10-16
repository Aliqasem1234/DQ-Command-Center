import { useEffect } from 'react';
import { useRouteError } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

/**
 * Shown when a page throws while rendering or loading (including a lazy
 * chunk that failed to download). Without it React Router falls back to its
 * built-in developer screen, and the outer ErrorBoundary never sees errors
 * that happen inside the router.
 */
export function RouteErrorPage() {
  const { t } = useTranslation();
  const error = useRouteError();

  useEffect(() => {
    console.error('Route error:', error);
  }, [error]);

  return (
    <div className="min-h-screen flex flex-col items-center justify-center text-center p-4 bg-slate-50 dark:bg-slate-950">
      <h1 className="text-2xl font-semibold text-slate-900 dark:text-slate-100 mb-2">
        {t('errors.somethingWentWrong')}
      </h1>
      <p className="text-sm text-slate-600 dark:text-slate-400 mb-6 max-w-md">{t('errors.unexpectedError')}</p>
      <div className="flex gap-3">
        <button type="button" onClick={() => window.location.reload()} className="btn-primary">
          {t('errors.reloadPage')}
        </button>
        <a href="/dashboard" className="btn-secondary">
          {t('common.goHome')}
        </a>
      </div>
    </div>
  );
}
