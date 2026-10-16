import { useTranslation } from 'react-i18next';
import { ChangePasswordCard } from './ProfilePage';

export function SecurityPage() {
  const { t } = useTranslation();
  return (
    <div className="max-w-2xl">
      <h1 className="text-2xl font-bold tracking-tight text-slate-900 mb-6">{t('nav.security')}</h1>
      <ChangePasswordCard />
    </div>
  );
}
