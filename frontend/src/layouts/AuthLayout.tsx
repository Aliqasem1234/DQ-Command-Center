import { Outlet } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Activity } from 'lucide-react';

export function AuthLayout() {
  const { t } = useTranslation();

  return (
    <div className="min-h-screen flex flex-col items-center justify-center py-8 px-4 bg-slate-50 dark:bg-slate-950">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-12 h-12 bg-primary-600 rounded-xl shadow-sm mb-4">
            <Activity className="w-6 h-6 text-white" />
          </div>
          <h1 className="text-xl font-bold text-slate-900">
            {t('app.name')}
          </h1>
          <p className="text-sm text-slate-500 mt-1.5">
            {t('app.tagline')}
          </p>
        </div>
        <Outlet />
      </div>
    </div>
  );
}
