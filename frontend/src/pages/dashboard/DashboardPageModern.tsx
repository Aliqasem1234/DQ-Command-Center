import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer
} from 'recharts';
import {
  AlertCircle, CheckCircle, Clock, TrendingUp, RefreshCw,
} from 'lucide-react';
import { dashboardService } from '../../services/dashboardService';
import { useThemeStore } from '../../store/themeStore';
import { EmptyState } from '../../components/common/EmptyState';
import type { DashboardHealthSummary, QualityIssueSummary } from '../../types';

const STATUS_KEY: Record<string, string> = {
  excellent: 'dashboard.statusExcellent',
  good: 'dashboard.statusGood',
  fair: 'dashboard.statusFair',
  poor: 'dashboard.statusPoor',
  critical: 'dashboard.statusCritical',
};

const TREND_KEY: Record<string, string> = {
  improving: 'dashboard.trendImproving',
  degrading: 'dashboard.trendDegrading',
  stable: 'dashboard.trendStable',
};

export function DashboardPageModern() {
  const { t } = useTranslation();
  const { mode } = useThemeStore();
  const isDark = mode === 'dark';
  const [metrics, setMetrics] = useState<DashboardHealthSummary | null>(null);
  const [issues, setIssues] = useState<QualityIssueSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchMetrics();
  }, []);

  const fetchMetrics = async () => {
    try {
      setError(null);
      const [summary, openIssues] = await Promise.all([
        dashboardService.getHealthSummary(30),
        dashboardService.getOpenIssues(5),
      ]);
      setMetrics(summary);
      setIssues(openIssues);
    } catch (err) {
      console.error('Failed to fetch dashboard metrics:', err);
      setError(t('dashboard.couldNotLoad'));
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    await fetchMetrics();
    setRefreshing(false);
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4"></div>
          <p className="text-slate-600">{t('dashboard.loadingDashboard')}</p>
        </div>
      </div>
    );
  }

  const getScoreColor = (score: number) => {
    if (score >= 90) return 'text-green-600';
    if (score >= 70) return 'text-yellow-600';
    return 'text-red-600';
  };

  const axisColor = isDark ? '#64748b' : '#94a3b8';
  const gridColor = isDark ? '#334155' : '#e2e8f0';
  const tooltipStyle = isDark
    ? { backgroundColor: '#1e293b', border: '1px solid #334155', color: '#f1f5f9' }
    : { backgroundColor: '#f8fafc', border: '1px solid #e2e8f0', color: '#0f172a' };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">{t('dashboard.title')}</h1>
          <p className="text-slate-600 text-sm mt-1">{t('dashboard.subtitle')}</p>
        </div>
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          className="btn-ghost flex items-center gap-2"
        >
          <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
          {t('common.refresh')}
        </button>
      </div>

      {/* Main Content */}
      <div>
        {error && (
          <div className="alert alert-error mb-6">
            <AlertCircle className="w-5 h-5 flex-shrink-0" />
            {error}
          </div>
        )}

        {/* Top Metrics */}
        {metrics && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
            {/* Overall Health Score */}
            <div className={`card-lg border-l-4 ${
              metrics.health_score >= 90 ? 'border-l-green-600' :
              metrics.health_score >= 70 ? 'border-l-yellow-600' :
              'border-l-red-600'
            }`}>
              <div className="flex items-start justify-between mb-4">
                <div>
                  <p className="text-slate-600 text-sm font-medium mb-1">{t('dashboard.overallHealth')}</p>
                  <p className={`text-4xl font-bold ${getScoreColor(metrics.health_score)}`}>
                    {Math.round(metrics.health_score)}%
                  </p>
                </div>
                {metrics.health_score >= 90 ? (
                  <CheckCircle className="w-6 h-6 text-green-600" />
                ) : metrics.health_score >= 70 ? (
                  <AlertCircle className="w-6 h-6 text-yellow-600" />
                ) : (
                  <AlertCircle className="w-6 h-6 text-red-600" />
                )}
              </div>
              <p className="text-xs text-slate-500 mt-4 pt-4 border-t border-slate-200">
                {t('dashboard.statusLabel', { status: t(STATUS_KEY[metrics.status] ?? 'dashboard.statusFair') })}
              </p>
            </div>

            {/* Open Issues */}
            <div className="card-lg border-l-4 border-l-orange-600">
              <div className="flex items-start justify-between mb-4">
                <div>
                  <p className="text-slate-600 text-sm font-medium mb-1">{t('dashboard.openIssues')}</p>
                  <p className="text-4xl font-bold text-orange-600">{metrics.open_issues}</p>
                </div>
                <AlertCircle className="w-6 h-6 text-orange-600" />
              </div>
              <p className="text-xs text-slate-500 mt-4 pt-4 border-t border-slate-200">
                {t('dashboard.criticalCount', { count: metrics.critical_issues })}
              </p>
            </div>

            {/* Datasets */}
            <div className="card-lg border-l-4 border-l-blue-600">
              <div className="flex items-start justify-between mb-4">
                <div>
                  <p className="text-slate-600 text-sm font-medium mb-1">{t('nav.datasets')}</p>
                  <p className="text-4xl font-bold text-blue-600">{metrics.total_datasets}</p>
                </div>
                <Clock className="w-6 h-6 text-blue-600" />
              </div>
              <p className="text-xs text-slate-500 mt-4 pt-4 border-t border-slate-200">
                {t('dashboard.beingMonitored')}
              </p>
            </div>

            {/* Quality Rules */}
            <div className="card-lg border-l-4 border-l-purple-600">
              <div className="flex items-start justify-between mb-4">
                <div>
                  <p className="text-slate-600 text-sm font-medium mb-1">{t('dataQuality.rules')}</p>
                  <p className="text-4xl font-bold text-purple-600">{metrics.total_quality_rules}</p>
                </div>
                <CheckCircle className="w-6 h-6 text-purple-600" />
              </div>
              <p className="text-xs text-slate-500 mt-4 pt-4 border-t border-slate-200">
                {t('common.active')}
              </p>
            </div>
          </div>
        )}

        {/* Charts Row */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
          {/* Quality Trend */}
          <div className="lg:col-span-2 card-lg">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="text-lg font-semibold text-slate-900">{t('dashboard.qualityTrend')}</h2>
                <p className="text-sm text-slate-600">{t('dashboard.last30Days')}</p>
              </div>
              {metrics && (
                <div className={`flex items-center gap-1 text-sm ${
                  metrics.recent_trend === 'improving' ? 'text-green-600' :
                  metrics.recent_trend === 'degrading' ? 'text-red-600' : 'text-slate-500'
                }`}>
                  <TrendingUp className="w-4 h-4" />
                  {t(TREND_KEY[metrics.recent_trend] ?? 'dashboard.trendStable')}
                </div>
              )}
            </div>
            {metrics && metrics.daily_trend.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={metrics.daily_trend}>
                  <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
                  <XAxis dataKey="date" stroke={axisColor} />
                  <YAxis stroke={axisColor} />
                  <Tooltip contentStyle={tooltipStyle} />
                  <Line
                    type="monotone"
                    dataKey="pass_rate"
                    stroke="#0ea5e9"
                    strokeWidth={2}
                    dot={false}
                    name={t('dashboard.passRateLegend')}
                  />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <EmptyState
                title={t('dashboard.noRunsTitle')}
                message={t('dashboard.noRunsMessage')}
              />
            )}
          </div>

          {/* Quality by Dimension */}
          {metrics && (
            <div className="card-lg">
              <h2 className="text-lg font-semibold text-slate-900 mb-6">{t('dashboard.qualityDimensions')}</h2>
              {Object.keys(metrics.dimensions).length > 0 ? (
                <div className="space-y-4">
                  {Object.entries(metrics.dimensions).map(([name, dim]) => (
                    <div key={name}>
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-medium text-slate-700">
                          {t(`dimensions.${name}`, { defaultValue: name.replace('_', ' ') })}
                        </span>
                        <span className="text-sm font-semibold text-slate-900">
                          {dim.score !== null ? `${Math.round(dim.score)}%` : t('common.noData')}
                        </span>
                      </div>
                      <div className="w-full h-2 bg-slate-200 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-primary-600 rounded-full transition-all"
                          style={{ width: `${Math.min(dim.score ?? 0, 100)}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <EmptyState title={t('dashboard.noRulesConfigured')} />
              )}
            </div>
          )}
        </div>

        {/* Recent Issues */}
        <div className="card-lg">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-lg font-semibold text-slate-900">{t('dashboard.recentIssues')}</h2>
              <p className="text-sm text-slate-600">{t('dashboard.recentIssuesSubtitle')}</p>
            </div>
          </div>

          {issues.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-200">
                    <th className="text-left py-3 px-4 font-medium text-slate-700">{t('dashboard.issueColumn')}</th>
                    <th className="text-left py-3 px-4 font-medium text-slate-700">{t('common.dataset')}</th>
                    <th className="text-left py-3 px-4 font-medium text-slate-700">{t('dataQuality.severity')}</th>
                    <th className="text-left py-3 px-4 font-medium text-slate-700">{t('common.status')}</th>
                    <th className="text-left py-3 px-4 font-medium text-slate-700">{t('dashboard.detectedColumn')}</th>
                  </tr>
                </thead>
                <tbody>
                  {issues.map((row) => (
                    <tr key={row.id} className="border-b border-slate-200 hover:bg-slate-50">
                      <td className="py-3 px-4 text-slate-900">{row.description || t('dashboard.untitledIssue')}</td>
                      <td className="py-3 px-4 text-slate-600">{row.dataset_name || '—'}</td>
                      <td className="py-3 px-4">
                        <span className={`badge ${
                          row.severity === 'critical' ? 'badge-error' :
                          row.severity === 'high' ? 'badge-warning' :
                          'badge-warning'
                        } capitalize`}>
                          {row.severity}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        <span className={`badge ${row.status === 'open' ? 'badge-error' : 'badge-info'} capitalize`}>
                          {row.status.replace('_', ' ')}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-slate-500">
                        {new Date(row.detected_at).toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <EmptyState
              icon={<CheckCircle className="w-10 h-10" />}
              title={t('dashboard.noOpenIssuesTitle')}
              message={t('dashboard.noOpenIssuesMessage')}
            />
          )}
        </div>
      </div>
    </div>
  );
}
