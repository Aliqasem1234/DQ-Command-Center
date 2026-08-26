import { useTranslation } from 'react-i18next';
import { AlertCircle, CheckCircle } from 'lucide-react';

export default function DataQualityMonitoringPage() {
  const { t } = useTranslation();

  const monitoring = [
    { id: 1, dataset: 'Customers', totalRules: 5, passedRules: 4, lastCheck: new Date(Date.now() - 3600000).toISOString(), status: 'warning' },
    { id: 2, dataset: 'Orders', totalRules: 8, passedRules: 8, lastCheck: new Date(Date.now() - 1800000).toISOString(), status: 'success' },
  ];

  return (
    <div>
      <h1 className="text-3xl font-bold text-slate-900 mb-6">{t('dataQuality.monitoring')}</h1>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="card-lg">
          <p className="text-sm text-slate-600 mb-1">{t('common.totalDatasets')}</p>
          <p className="text-3xl font-bold text-slate-900">2</p>
        </div>
        <div className="card-lg">
          <p className="text-sm text-slate-600 mb-1">{t('common.activeRules')}</p>
          <p className="text-3xl font-bold text-primary-600">13</p>
        </div>
        <div className="card-lg">
          <p className="text-sm text-slate-600 mb-1">{t('common.healthScore')}</p>
          <p className="text-3xl font-bold text-green-600">92%</p>
        </div>
      </div>

      <div className="card-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="border-b border-slate-200 bg-slate-50">
              <tr>
                <th className="text-left px-6 py-3 text-sm font-semibold text-slate-900">{t('common.dataset')}</th>
                <th className="text-left px-6 py-3 text-sm font-semibold text-slate-900">{t('common.rules')}</th>
                <th className="text-left px-6 py-3 text-sm font-semibold text-slate-900">{t('common.status')}</th>
                <th className="text-left px-6 py-3 text-sm font-semibold text-slate-900">{t('common.lastCheck')}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {monitoring.map((item) => (
                <tr key={item.id} className="hover:bg-slate-50">
                  <td className="px-6 py-4 text-sm font-medium text-slate-900">{item.dataset}</td>
                  <td className="px-6 py-4 text-sm text-slate-600">{item.passedRules}/{item.totalRules}</td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                      {item.status === 'success' ? (
                        <>
                          <CheckCircle size={18} className="text-green-600" />
                          <span className="text-sm text-green-600 font-medium">Healthy</span>
                        </>
                      ) : (
                        <>
                          <AlertCircle size={18} className="text-yellow-600" />
                          <span className="text-sm text-yellow-600 font-medium">Warning</span>
                        </>
                      )}
                    </div>
                  </td>
                  <td className="px-6 py-4 text-sm text-slate-600">
                    {new Date(item.lastCheck).toLocaleString()}
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
