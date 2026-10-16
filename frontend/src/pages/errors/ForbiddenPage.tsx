import { Link as RouterLink } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

export function ForbiddenPage() {
  const { t } = useTranslation();

  return (
    <div className="min-h-screen flex flex-col items-center justify-center text-center p-4">
      <h1 className="text-9xl font-bold text-red-600">403</h1>
      <h2 className="text-2xl font-semibold text-slate-900 mb-6 mt-4">
        {t('common.forbidden')}
      </h2>
      <RouterLink
        to="/dashboard"
        className="btn-primary"
      >
        {t('common.goHome')}
      </RouterLink>
    </div>
  );
}
