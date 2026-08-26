import { useTranslation } from 'react-i18next';

interface EmptyStateProps {
  icon?: React.ReactNode;
  title?: string;
  message?: string;
  action?: React.ReactNode;
}

export function EmptyState({ icon, title, message, action }: EmptyStateProps) {
  const { t } = useTranslation();

  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      {icon && <div className="mb-4 text-slate-400">{icon}</div>}
      <h3 className="text-lg font-semibold text-slate-900 mb-2">
        {title || t('common.noData')}
      </h3>
      {message && (
        <p className="text-sm text-slate-600 mb-4 max-w-sm">
          {message}
        </p>
      )}
      {action && <div>{action}</div>}
    </div>
  );
}
