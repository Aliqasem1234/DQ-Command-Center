import { Link as RouterLink } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

export function NotFoundPage() {
  const { t } = useTranslation();

  return (
    <div className="min-h-screen flex flex-col items-center justify-center text-center p-4">
      <h1 className="text-9xl font-bold text-primary-600">404</h1>
      <h2 className="text-2xl font-semibold text-slate-900 mb-6 mt-4">
        {t('common.pageNotFound')}
      </h2>
      <RouterLink
        to="/dashboard"
        className="px-6 py-2 bg-primary-600 text-white rounded-lg font-medium hover:bg-primary-700 transition-colors"
      >
        {t('common.goHome')}
      </RouterLink>
    </div>
  );
}
