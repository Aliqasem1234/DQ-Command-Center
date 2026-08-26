import { useTranslation } from 'react-i18next';
import { useQuery } from '@tanstack/react-query';
import { auditService } from '../../services/auditService';
import { getErrorMessage } from '../../services/api';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { EmptyState } from '../../components/common/EmptyState';

const ACTION_BADGE: Record<string, string> = {
  CREATE: 'badge-success',
  UPDATE: 'badge-info',
  CLEAN: 'badge-info',
  DELETE: 'badge-error',
  REVOKE: 'badge-error',
};

export function AuditLogPage() {
  const { t } = useTranslation();

  const { data, isLoading, error } = useQuery({
    queryKey: ['audit-logs'],
    queryFn: () => auditService.list(1, 50),
  });

  const logs = data?.items ?? [];

  return (
    <div>
      <h1 className="text-2xl font-bold tracking-tight text-slate-900 mb-6">{t('nav.audit')}</h1>

      <div className="card-lg overflow-hidden">
        {isLoading ? (
          <LoadingSpinner />
        ) : error ? (
          <div className="p-6 text-sm text-red-700">{getErrorMessage(error)}</div>
        ) : logs.length === 0 ? (
          <EmptyState title={t('common.noData')} />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr>
                  <th>{t('common.action')}</th>
                  <th>{t('audit.entityType')}</th>
                  <th>{t('common.name')}</th>
                  <th>{t('auth.user')}</th>
                  <th>{t('common.timestamp')}</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((log) => (
                  <tr key={log.id}>
                    <td>
                      <span className={`badge ${ACTION_BADGE[log.action] ?? 'badge-info'}`}>
                        <span className="badge-dot" />
                        {log.action}
                      </span>
                    </td>
                    <td className="text-slate-500">{log.entity_type}</td>
                    <td className="font-medium text-slate-800">{log.entity_name || '—'}</td>
                    <td className="text-slate-500">{log.user_email || '—'}</td>
                    <td className="text-slate-500">
                      {new Date(log.created_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
