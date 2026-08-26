import { useTranslation } from 'react-i18next';
import { useQuery } from '@tanstack/react-query';
import { AlertCircle, CheckCircle } from 'lucide-react';
import { dataQualityService } from '../../services/dataQualityService';
import { getErrorMessage } from '../../services/api';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { EmptyState } from '../../components/common/EmptyState';

export default function DataQualityMonitoringPage() {
  const { t } = useTranslation();

  const { data: metrics, isLoading, error } = useQuery({
    queryKey: ['data-quality-metrics'],
    queryFn: () => dataQualityService.getMetrics(),
  });

  if (isLoading) {
    return <LoadingSpinner />;
  }

  if (error) {
    return (
      <div>
        <h1 className="text-3xl font-bold text-slate-900 mb-6">{t('dataQuality.monitoring')}</h1>
        <div className="card-lg p-6 text-sm text-red-700">{getErrorMessage(error)}</div>
      </div>
    );
  }

  const dimensionStats = metrics?.dimension_stats ?? [];

  return (
    <div>
      <h1 className="text-3xl font-bold text-slate-900 mb-6">{t('dataQuality.monitoring')}</h1>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="card-lg">
          <p className="text-sm text-slate-600 mb-1">{t('common.totalDatasets')}</p>
          <p className="text-3xl font-bold text-slate-900">{metrics?.total_rules ?? 0}</p>
        </div>
        <div className="card-lg">
          <p className="text-sm text-slate-600 mb-1">{t('common.activeRules')}</p>
          <p className="text-3xl font-bold text-primary-600">{metrics?.active_rules ?? 0}</p>
        </div>
        <div className="card-lg">
          <p className="text-sm text-slate-600 mb-1">{t('common.healthScore')}</p>
          <p
            className={`text-3xl font-bold ${
              (metrics?.overall_pass_rate ?? 0) >= 90
                ? 'text-green-600'
                : (metrics?.overall_pass_rate ?? 0) >= 70
                ? 'text-yellow-600'
                : 'text-red-600'
            }`}
          >
            {Math.round(metrics?.overall_pass_rate ?? 0)}%
          </p>
        </div>
      </div>

      <div className="card-lg overflow-hidden">
        {dimensionStats.length === 0 ? (
          <EmptyState
            title={t('common.noData')}
            message={t('dataQuality.noMonitoringData')}
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="border-b border-slate-200 bg-slate-50">
                <tr>
                  <th className="text-left px-6 py-3 text-sm font-semibold text-slate-900">{t('dataQuality.dimensions')}</th>
                  <th className="text-left px-6 py-3 text-sm font-semibold text-slate-900">{t('common.rules')}</th>
                  <th className="text-left px-6 py-3 text-sm font-semibold text-slate-900">{t('common.status')}</th>
                  <th className="text-left px-6 py-3 text-sm font-semibold text-slate-900">{t('common.lastCheck')}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {dimensionStats.map((item) => {
                  const total = item.passed_results + item.failed_results;
                  const isHealthy = total === 0 || item.failed_results === 0;
                  return (
                    <tr key={item.dimension} className="hover:bg-slate-50">
                      <td className="px-6 py-4 text-sm font-medium text-slate-900 capitalize">{item.dimension}</td>
                      <td className="px-6 py-4 text-sm text-slate-600">{item.active_rules}/{item.total_rules}</td>
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-2">
                          {isHealthy ? (
                            <>
                              <CheckCircle size={18} className="text-green-600" />
                              <span className="text-sm text-green-600 font-medium">{t('dataQuality.healthy')}</span>
                            </>
                          ) : (
                            <>
                              <AlertCircle size={18} className="text-yellow-600" />
                              <span className="text-sm text-yellow-600 font-medium">{t('dataQuality.warning')}</span>
                            </>
                          )}
                        </div>
                      </td>
                      <td className="px-6 py-4 text-sm text-slate-600">
                        {item.last_execution ? new Date(item.last_execution).toLocaleString() : '—'}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
