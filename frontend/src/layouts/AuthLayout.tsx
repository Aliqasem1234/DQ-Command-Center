import { Outlet } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

export function AuthLayout() {
  const { t } = useTranslation();

  return (
    <div className="min-h-screen flex flex-col items-center justify-center py-4">
      <div className="w-full max-w-sm px-4">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-primary-600">
            {t('app.name')}
          </h1>
          <p className="text-sm text-slate-600 mt-2">
            {t('app.tagline')}
          </p>
        </div>
        <Outlet />
      </div>
    </div>
  );
}
