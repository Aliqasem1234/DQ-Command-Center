import { useTranslation } from 'react-i18next';
import { useQuery } from '@tanstack/react-query';
import { AlertCircle, CheckCircle, ListChecks, Zap, Gauge, MinusCircle, Activity, Upload } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { dashboardService } from '../../services/dashboardService';
import { dataQualityService } from '../../services/dataQualityService';
import { getErrorMessage } from '../../services/api';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { EmptyState } from '../../components/common/EmptyState';

export default function DataQualityMonitoringPage() {
  const { t } = useTranslation();

  const navigate = useNavigate();
  const { data: metrics, isLoading, error } = useQuery({
    queryKey: ['data-quality-metrics'],
    queryFn: () => dataQualityService.getMetrics(),
  });
  // Health uses the same definition as the dashboard (average quality score
  // of the user's scanned datasets). The metrics endpoint's pass rate counts
  // check *runs* that passed, and automatic checks only record runs while
  // they fail - so it read 0% for every real user.
  const { data: summary, isLoading: summaryLoading } = useQuery({
    queryKey: ['dashboard-summary'],
    queryFn: () => dashboardService.getHealthSummary(30),
  });

  if (isLoading || summaryLoading) {
    return <LoadingSpinner />;
  }

  if (error) {
    return (
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 mb-6">{t('dataQuality.monitoring')}</h1>
        <div className="card-lg p-6 text-sm text-red-700">{getErrorMessage(error)}</div>
      </div>
    );
  }

  const dimensionStats = metrics?.dimension_stats ?? [];
  const health = summary?.health_score ?? null;
  const hasDatasets = (summary?.total_datasets ?? 0) > 0;

  // Nothing to monitor yet: say so and offer the next step instead of a
  // grid of zeros and "healthy" labels for checks that never ran.
  if ((metrics?.total_rules ?? 0) === 0) {
    return (
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 mb-6">{t('dataQuality.monitoring')}</h1>
        <div className="card-lg">
          <EmptyState
            icon={<Activity size={40} />}
            title={t('dataQuality.monitoringEmptyTitle')}
            message={t(hasDatasets ? 'dataQuality.monitoringEmptyScan' : 'dataQuality.monitoringEmptyUpload')}
            action={
              <button
                className="btn-primary flex items-center gap-2"
                onClick={() => navigate(hasDatasets ? '/datasets' : '/datasets?upload=1')}
              >
                <Upload size={16} />
                {t(hasDatasets ? 'dataQuality.goToDatasets' : 'datasets.uploadFirst')}
              </button>
            }
          />
        </div>
      </div>
    );
  }

  return (
    <div>
      <h1 className="text-2xl font-bold tracking-tight text-slate-900 mb-6">{t('dataQuality.monitoring')}</h1>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-5 mb-6">
        <div className="card-lg">
          <div className="icon-badge icon-badge-slate">
            <ListChecks className="w-5 h-5" />
          </div>
          <p className="text-sm text-slate-500 mt-3">{t('common.rules')}</p>
          <p className="text-3xl font-bold tracking-tight text-slate-900 mt-0.5">{metrics?.total_rules ?? 0}</p>
        </div>
        <div className="card-lg">
          <div className="icon-badge icon-badge-blue">
            <Zap className="w-5 h-5" />
          </div>
          <p className="text-sm text-slate-500 mt-3">{t('common.activeRules')}</p>
          <p className="text-3xl font-bold text-primary-600 mt-0.5">{metrics?.active_rules ?? 0}</p>
        </div>
        <div className="card-lg">
          <div className={`icon-badge ${
            health === null ? 'icon-badge-slate'
            : health >= 90 ? 'icon-badge-green'
            : health >= 70 ? 'icon-badge-orange'
            : 'icon-badge-red'
          }`}>
            <Gauge className="w-5 h-5" />
          </div>
          <p className="text-sm text-slate-500 mt-3">{t('common.healthScore')}</p>
          {health === null ? (
            <>
              <p className="text-3xl font-bold mt-0.5 text-slate-400">—</p>
              <p className="text-xs text-slate-500 mt-1">{t('dashboard.healthNoData')}</p>
            </>
          ) : (
            <p
              className={`text-3xl font-bold mt-0.5 ${
                health >= 90 ? 'text-green-600' : health >= 70 ? 'text-yellow-600' : 'text-red-600'
              }`}
            >
              {Math.round(health)}%
            </p>
          )}
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
                  const hasData = item.total_rules > 0 && total > 0;
                  const isHealthy = hasData && item.failed_results === 0;
                  return (
                    <tr key={item.dimension} className="hover:bg-slate-50">
                      <td className="px-6 py-4 text-sm font-medium text-slate-900">{t(`dimensions.${item.dimension}`, { defaultValue: item.dimension })}</td>
                      <td className="px-6 py-4 text-sm text-slate-600">{item.active_rules}/{item.total_rules}</td>
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-2">
                          {!hasData ? (
                            <>
                              <MinusCircle size={18} className="text-slate-400" />
                              <span className="text-sm text-slate-500 font-medium">{t('dataQuality.noData')}</span>
                            </>
                          ) : isHealthy ? (
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
