import { useTranslation } from 'react-i18next';
import { useQuery } from '@tanstack/react-query';
import { auditService } from '../../services/auditService';
import { getErrorMessage } from '../../services/api';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { EmptyState } from '../../components/common/EmptyState';

export function AuditLogPage() {
  const { t } = useTranslation();

  const { data, isLoading, error } = useQuery({
    queryKey: ['audit-logs'],
    queryFn: () => auditService.list(1, 50),
  });

  const logs = data?.items ?? [];

  return (
    <div>
      <h1 className="text-3xl font-bold text-slate-900 mb-6">{t('nav.audit')}</h1>

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
              <thead className="border-b border-slate-200 bg-slate-50">
                <tr>
                  <th className="text-left px-6 py-3 text-sm font-semibold text-slate-900">{t('common.action')}</th>
                  <th className="text-left px-6 py-3 text-sm font-semibold text-slate-900">{t('audit.entityType')}</th>
                  <th className="text-left px-6 py-3 text-sm font-semibold text-slate-900">{t('common.name')}</th>
                  <th className="text-left px-6 py-3 text-sm font-semibold text-slate-900">{t('auth.user')}</th>
                  <th className="text-left px-6 py-3 text-sm font-semibold text-slate-900">{t('common.timestamp')}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {logs.map((log) => (
                  <tr key={log.id} className="hover:bg-slate-50">
                    <td className="px-6 py-4 text-sm text-slate-900">{log.action}</td>
                    <td className="px-6 py-4 text-sm text-slate-600">{log.entity_type}</td>
                    <td className="px-6 py-4 text-sm text-slate-600">{log.entity_name || '—'}</td>
                    <td className="px-6 py-4 text-sm text-slate-600">{log.user_email || '—'}</td>
                    <td className="px-6 py-4 text-sm text-slate-600">
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
