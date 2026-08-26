import { useEffect, useState } from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer
} from 'recharts';
import {
  AlertCircle, CheckCircle, Clock, TrendingUp,
  RefreshCw, Bell, User, LogOut
} from 'lucide-react';
import { dashboardService } from '../../services/dashboardService';
import { useAuth } from '../../hooks/useAuth';
import { EmptyState } from '../../components/common/EmptyState';
import type { DashboardHealthSummary, QualityIssueSummary } from '../../types';

export function DashboardPageModern() {
  const { logout } = useAuth();
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
      setError('Could not load dashboard data. Please try again.');
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
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4"></div>
          <p className="text-slate-600">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  const getScoreColor = (score: number) => {
    if (score >= 90) return 'text-green-600';
    if (score >= 70) return 'text-yellow-600';
    return 'text-red-600';
  };

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="bg-white border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Data Quality Dashboard</h1>
            <p className="text-slate-600 text-sm mt-1">Real-time quality metrics and insights</p>
          </div>
          
          <div className="flex items-center gap-4">
            <button
              onClick={handleRefresh}
              disabled={refreshing}
              className="btn-ghost flex items-center gap-2"
            >
              <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
              Refresh
            </button>
            
            <button className="btn-ghost" title="Notifications (coming soon)" disabled>
              <Bell className="w-4 h-4" />
            </button>

            <div className="border-l border-slate-200 pl-4 flex items-center gap-2">
              <div className="w-8 h-8 bg-primary-100 rounded-full flex items-center justify-center">
                <User className="w-4 h-4 text-primary-600" />
              </div>
              <button className="btn-ghost p-0" onClick={() => logout()} title="Log out">
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-6 py-8">
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-3 text-sm text-red-800">
            <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0" />
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
                  <p className="text-slate-600 text-sm font-medium mb-1">Overall Health</p>
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
              <p className="text-xs text-slate-500 mt-4 pt-4 border-t border-slate-200 capitalize">
                Status: {metrics.status}
              </p>
            </div>

            {/* Open Issues */}
            <div className="card-lg border-l-4 border-l-orange-600">
              <div className="flex items-start justify-between mb-4">
                <div>
                  <p className="text-slate-600 text-sm font-medium mb-1">Open Issues</p>
                  <p className="text-4xl font-bold text-orange-600">{metrics.open_issues}</p>
                </div>
                <AlertCircle className="w-6 h-6 text-orange-600" />
              </div>
              <p className="text-xs text-slate-500 mt-4 pt-4 border-t border-slate-200">
                {metrics.critical_issues} critical
              </p>
            </div>

            {/* Datasets */}
            <div className="card-lg border-l-4 border-l-blue-600">
              <div className="flex items-start justify-between mb-4">
                <div>
                  <p className="text-slate-600 text-sm font-medium mb-1">Datasets</p>
                  <p className="text-4xl font-bold text-blue-600">{metrics.total_datasets}</p>
                </div>
                <Clock className="w-6 h-6 text-blue-600" />
              </div>
              <p className="text-xs text-slate-500 mt-4 pt-4 border-t border-slate-200">
                Being monitored
              </p>
            </div>

            {/* Quality Rules */}
            <div className="card-lg border-l-4 border-l-purple-600">
              <div className="flex items-start justify-between mb-4">
                <div>
                  <p className="text-slate-600 text-sm font-medium mb-1">Quality Rules</p>
                  <p className="text-4xl font-bold text-purple-600">{metrics.total_quality_rules}</p>
                </div>
                <CheckCircle className="w-6 h-6 text-purple-600" />
              </div>
              <p className="text-xs text-slate-500 mt-4 pt-4 border-t border-slate-200">
                Active
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
                <h2 className="text-lg font-semibold text-slate-900">Quality Trend</h2>
                <p className="text-sm text-slate-600">Last 30 days</p>
              </div>
              {metrics && (
                <div className={`flex items-center gap-1 text-sm ${
                  metrics.recent_trend === 'improving' ? 'text-green-600' :
                  metrics.recent_trend === 'degrading' ? 'text-red-600' : 'text-slate-500'
                }`}>
                  <TrendingUp className="w-4 h-4" />
                  {metrics.recent_trend}
                </div>
              )}
            </div>
            {metrics && metrics.daily_trend.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={metrics.daily_trend}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="date" stroke="#94a3b8" />
                  <YAxis stroke="#94a3b8" />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#f8fafc', border: '1px solid #e2e8f0' }}
                  />
                  <Line
                    type="monotone"
                    dataKey="pass_rate"
                    stroke="#0ea5e9"
                    strokeWidth={2}
                    dot={false}
                    name="Pass Rate %"
                  />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <EmptyState
                title="No quality check runs yet"
                message="Once quality rules have been executed, the pass-rate trend will appear here."
              />
            )}
          </div>

          {/* Quality by Dimension */}
          {metrics && (
            <div className="card-lg">
              <h2 className="text-lg font-semibold text-slate-900 mb-6">Quality Dimensions</h2>
              {Object.keys(metrics.dimensions).length > 0 ? (
                <div className="space-y-4">
                  {Object.entries(metrics.dimensions).map(([name, dim]) => (
                    <div key={name}>
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-medium text-slate-700 capitalize">
                          {name.replace('_', ' ')}
                        </span>
                        <span className="text-sm font-semibold text-slate-900">
                          {dim.score !== null ? `${Math.round(dim.score)}%` : 'No data'}
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
                <EmptyState title="No quality rules configured yet" />
              )}
            </div>
          )}
        </div>

        {/* Recent Issues */}
        <div className="card-lg">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-lg font-semibold text-slate-900">Recent Issues</h2>
              <p className="text-sm text-slate-600">Most recently detected open issues</p>
            </div>
          </div>

          {issues.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-200">
                    <th className="text-left py-3 px-4 font-medium text-slate-700">Issue</th>
                    <th className="text-left py-3 px-4 font-medium text-slate-700">Dataset</th>
                    <th className="text-left py-3 px-4 font-medium text-slate-700">Severity</th>
                    <th className="text-left py-3 px-4 font-medium text-slate-700">Status</th>
                    <th className="text-left py-3 px-4 font-medium text-slate-700">Detected</th>
                  </tr>
                </thead>
                <tbody>
                  {issues.map((row) => (
                    <tr key={row.id} className="border-b border-slate-200 hover:bg-slate-50">
                      <td className="py-3 px-4 text-slate-900">{row.description || 'Untitled issue'}</td>
                      <td className="py-3 px-4 text-slate-600">{row.dataset_name || '—'}</td>
                      <td className="py-3 px-4">
                        <span className={`inline-block px-2 py-1 rounded text-xs font-medium capitalize ${
                          row.severity === 'critical' ? 'bg-red-100 text-red-700' :
                          row.severity === 'high' ? 'bg-orange-100 text-orange-700' :
                          'bg-yellow-100 text-yellow-700'
                        }`}>
                          {row.severity}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        <span className={`inline-block px-2 py-1 rounded text-xs font-medium capitalize ${
                          row.status === 'open' ? 'bg-red-100 text-red-700' :
                          'bg-blue-100 text-blue-700'
                        }`}>
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
              title="No open issues"
              message="Everything is passing quality checks right now."
            />
          )}
        </div>
      </div>
    </div>
  );
}
