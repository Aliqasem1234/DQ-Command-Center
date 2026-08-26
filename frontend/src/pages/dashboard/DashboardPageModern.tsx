import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, AreaChart, Area,
} from 'recharts';
import {
  AlertCircle, AlertTriangle, CheckCircle, Database, ShieldCheck,
  TrendingUp, TrendingDown, Minus, RefreshCw,
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

const TREND_ICON: Record<string, typeof TrendingUp> = {
  improving: TrendingUp,
  degrading: TrendingDown,
  stable: Minus,
};

// Each dimension gets a stable, distinct accent so the same metric always
// reads the same color anywhere it appears in the app.
const DIMENSION_COLOR: Record<string, { bar: string; dot: string }> = {
  accuracy: { bar: 'bg-blue-500', dot: 'bg-blue-500' },
  completeness: { bar: 'bg-green-500', dot: 'bg-green-500' },
  consistency: { bar: 'bg-orange-500', dot: 'bg-orange-500' },
  validity: { bar: 'bg-purple-500', dot: 'bg-purple-500' },
  uniqueness: { bar: 'bg-cyan-500', dot: 'bg-cyan-500' },
  timeliness: { bar: 'bg-pink-500', dot: 'bg-pink-500' },
};

function scoreTextColor(score: number) {
  if (score >= 90) return 'text-green-600 dark:text-green-400';
  if (score >= 70) return 'text-yellow-600 dark:text-yellow-400';
  return 'text-red-600 dark:text-red-400';
}

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
      <div className="flex items-center justify-center py-24">
        <div className="text-center">
          <div className="animate-spin rounded-full h-10 w-10 border-4 border-slate-200 dark:border-slate-800 border-t-primary-600 mx-auto mb-4" />
          <p className="text-slate-500 text-sm">{t('dashboard.loadingDashboard')}</p>
        </div>
      </div>
    );
  }

  const axisColor = isDark ? '#64748b' : '#94a3b8';
  const gridColor = isDark ? '#334155' : '#e2e8f0';
  const tooltipStyle = isDark
    ? { backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px', color: '#f1f5f9', fontSize: '13px' }
    : { backgroundColor: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '8px', color: '#0f172a', fontSize: '13px' };

  const TrendIcon = metrics ? TREND_ICON[metrics.recent_trend] ?? Minus : Minus;
  const trendColor = metrics?.recent_trend === 'improving' ? 'text-green-600 dark:text-green-400'
    : metrics?.recent_trend === 'degrading' ? 'text-red-600 dark:text-red-400'
    : 'text-slate-500 dark:text-slate-400';

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">{t('dashboard.title')}</h1>
          <p className="text-slate-500 text-sm mt-1">{t('dashboard.subtitle')}</p>
        </div>
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          className="btn-secondary flex items-center gap-2"
        >
          <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
          {t('common.refresh')}
        </button>
      </div>

      {error && (
        <div className="alert alert-error mb-6">
          <AlertCircle className="w-5 h-5 flex-shrink-0" />
          {error}
        </div>
      )}

      {/* Top Metrics */}
      {metrics && (
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-5 mb-6">
          {/* Overall Health Score - the only card with a real historical
              trend behind it, so it's the only one that earns a sparkline. */}
          <div className="card-lg">
            <div className="flex items-start justify-between">
              <div className="icon-badge icon-badge-red">
                <ShieldCheck className="w-5 h-5" />
              </div>
              {metrics.daily_trend.length > 1 && (
                <div className="w-20 h-10 -mt-1 -mr-2">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={metrics.daily_trend}>
                      <defs>
                        <linearGradient id="healthSpark" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="#0ea5e9" stopOpacity={0.35} />
                          <stop offset="100%" stopColor="#0ea5e9" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <Area type="monotone" dataKey="pass_rate" stroke="#0ea5e9" strokeWidth={1.5} fill="url(#healthSpark)" />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              )}
            </div>
            <p className="text-slate-500 text-sm font-medium mt-3">{t('dashboard.overallHealth')}</p>
            <p className={`text-3xl font-bold mt-0.5 ${scoreTextColor(metrics.health_score)}`}>
              {Math.round(metrics.health_score)}%
            </p>
            <p className="text-xs text-slate-500 mt-3 pt-3 border-t border-slate-100 dark:border-slate-800">
              {t('dashboard.statusLabel', { status: t(STATUS_KEY[metrics.status] ?? 'dashboard.statusFair') })}
            </p>
          </div>

          {/* Open Issues */}
          <div className="card-lg">
            <div className="icon-badge icon-badge-orange">
              <AlertTriangle className="w-5 h-5" />
            </div>
            <p className="text-slate-500 text-sm font-medium mt-3">{t('dashboard.openIssues')}</p>
            <p className="text-3xl font-bold mt-0.5 text-slate-900">{metrics.open_issues}</p>
            <p className="text-xs text-slate-500 mt-3 pt-3 border-t border-slate-100 dark:border-slate-800">
              {t('dashboard.criticalCount', { count: metrics.critical_issues })}
            </p>
          </div>

          {/* Datasets */}
          <div className="card-lg">
            <div className="icon-badge icon-badge-blue">
              <Database className="w-5 h-5" />
            </div>
            <p className="text-slate-500 text-sm font-medium mt-3">{t('nav.datasets')}</p>
            <p className="text-3xl font-bold mt-0.5 text-slate-900">{metrics.total_datasets}</p>
            <p className="text-xs text-slate-500 mt-3 pt-3 border-t border-slate-100 dark:border-slate-800">
              {t('dashboard.beingMonitored')}
            </p>
          </div>

          {/* Quality Rules */}
          <div className="card-lg">
            <div className="icon-badge icon-badge-purple">
              <CheckCircle className="w-5 h-5" />
            </div>
            <p className="text-slate-500 text-sm font-medium mt-3">{t('dataQuality.rules')}</p>
            <p className="text-3xl font-bold mt-0.5 text-slate-900">{metrics.total_quality_rules}</p>
            <p className="text-xs text-slate-500 mt-3 pt-3 border-t border-slate-100 dark:border-slate-800">
              {t('common.active')}
            </p>
          </div>
        </div>
      )}

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5 mb-6">
        {/* Quality Trend */}
        <div className="lg:col-span-2 card-lg">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-base font-semibold text-slate-900">{t('dashboard.qualityTrend')}</h2>
              <p className="text-sm text-slate-500">{t('dashboard.last30Days')}</p>
            </div>
            {metrics && (
              <div className={`flex items-center gap-1.5 text-sm font-medium ${trendColor}`}>
                <TrendIcon className="w-4 h-4" />
                {t(TREND_KEY[metrics.recent_trend] ?? 'dashboard.trendStable')}
              </div>
            )}
          </div>
          {metrics && metrics.daily_trend.length > 0 ? (
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={metrics.daily_trend}>
                <defs>
                  <linearGradient id="trendLine" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#0ea5e9" stopOpacity={0.2} />
                    <stop offset="100%" stopColor="#0ea5e9" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke={gridColor} vertical={false} />
                <XAxis dataKey="date" stroke={axisColor} fontSize={12} tickLine={false} axisLine={false} />
                <YAxis stroke={axisColor} fontSize={12} tickLine={false} axisLine={false} width={36} />
                <Tooltip contentStyle={tooltipStyle} />
                <Line
                  type="monotone"
                  dataKey="pass_rate"
                  stroke="#0ea5e9"
                  strokeWidth={2.5}
                  dot={false}
                  activeDot={{ r: 5 }}
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
            <h2 className="text-base font-semibold text-slate-900 mb-5">{t('dashboard.qualityDimensions')}</h2>
            {Object.keys(metrics.dimensions).length > 0 ? (
              <div className="space-y-4">
                {Object.entries(metrics.dimensions).map(([name, dim]) => {
                  const color = DIMENSION_COLOR[name] ?? { bar: 'bg-primary-600', dot: 'bg-primary-600' };
                  return (
                    <div key={name}>
                      <div className="flex items-center justify-between mb-1.5">
                        <span className="flex items-center gap-2 text-sm font-medium text-slate-700">
                          <span className={`w-2 h-2 rounded-full flex-shrink-0 ${color.dot}`} />
                          {t(`dimensions.${name}`, { defaultValue: name.replace('_', ' ') })}
                        </span>
                        <span className="text-sm font-semibold text-slate-900">
                          {dim.score !== null ? `${Math.round(dim.score)}%` : t('common.noData')}
                        </span>
                      </div>
                      <div className="w-full h-1.5 bg-slate-100 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all ${color.bar}`}
                          style={{ width: `${Math.min(dim.score ?? 0, 100)}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <EmptyState title={t('dashboard.noRulesConfigured')} />
            )}
          </div>
        )}
      </div>

      {/* Recent Issues */}
      <div className="card-lg overflow-hidden !p-0">
        <div className="flex items-center justify-between px-6 pt-6 pb-4">
          <div>
            <h2 className="text-base font-semibold text-slate-900">{t('dashboard.recentIssues')}</h2>
            <p className="text-sm text-slate-500">{t('dashboard.recentIssuesSubtitle')}</p>
          </div>
        </div>

        {issues.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr>
                  <th>{t('dashboard.issueColumn')}</th>
                  <th>{t('common.dataset')}</th>
                  <th>{t('dataQuality.severity')}</th>
                  <th>{t('common.status')}</th>
                  <th>{t('dashboard.detectedColumn')}</th>
                </tr>
              </thead>
              <tbody>
                {issues.map((row) => (
                  <tr key={row.id}>
                    <td className="text-slate-800 font-medium">{row.description || t('dashboard.untitledIssue')}</td>
                    <td className="text-slate-500">{row.dataset_name || '—'}</td>
                    <td>
                      <span className={`badge capitalize ${
                        row.severity === 'critical' ? 'badge-error' :
                        row.severity === 'high' ? 'badge-warning' :
                        'badge-warning'
                      }`}>
                        <span className="badge-dot" />
                        {row.severity}
                      </span>
                    </td>
                    <td>
                      <span className={`badge capitalize ${row.status === 'open' ? 'badge-error' : 'badge-info'}`}>
                        <span className="badge-dot" />
                        {row.status.replace('_', ' ')}
                      </span>
                    </td>
                    <td className="text-slate-500">
                      {new Date(row.detected_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="pb-6">
            <EmptyState
              icon={<CheckCircle className="w-10 h-10 text-green-500" />}
              title={t('dashboard.noOpenIssuesTitle')}
              message={t('dashboard.noOpenIssuesMessage')}
            />
          </div>
        )}
      </div>
    </div>
  );
}
