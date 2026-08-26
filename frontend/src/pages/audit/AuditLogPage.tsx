import { useTranslation } from 'react-i18next';

export function AuditLogPage() {
  const { t } = useTranslation();

  const auditLogs = [
    { id: 1, action: 'User Login', user: 'admin@example.com', timestamp: new Date(Date.now() - 3600000).toISOString() },
    { id: 2, action: 'Dataset Updated', user: 'user@example.com', timestamp: new Date(Date.now() - 7200000).toISOString() },
  ];

  return (
    <div>
      <h1 className="text-3xl font-bold text-slate-900 mb-6">{t('nav.audit')}</h1>

      <div className="card-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="border-b border-slate-200 bg-slate-50">
              <tr>
                <th className="text-left px-6 py-3 text-sm font-semibold text-slate-900">{t('common.action')}</th>
                <th className="text-left px-6 py-3 text-sm font-semibold text-slate-900">{t('auth.user')}</th>
                <th className="text-left px-6 py-3 text-sm font-semibold text-slate-900">{t('common.timestamp')}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {auditLogs.map((log) => (
                <tr key={log.id} className="hover:bg-slate-50">
                  <td className="px-6 py-4 text-sm text-slate-900">{log.action}</td>
                  <td className="px-6 py-4 text-sm text-slate-600">{log.user}</td>
                  <td className="px-6 py-4 text-sm text-slate-600">
                    {new Date(log.timestamp).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
