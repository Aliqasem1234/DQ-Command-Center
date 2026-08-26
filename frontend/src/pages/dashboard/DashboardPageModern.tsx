import { useEffect, useState } from 'react';
import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell
} from 'recharts';
import {
  AlertCircle, CheckCircle, Clock, TrendingDown, TrendingUp,
  Filter, Download, RefreshCw, Settings, Bell, User, LogOut
} from 'lucide-react';

interface HealthMetrics {
  overall_health_score: number;
  dimensions: Record<string, number>;
  open_issues: number;
  datasets: number;
  quality_rules: number;
}

interface TrendPoint {
  date: string;
  pass_rate: number;
}

export function DashboardPageModern() {
  const [metrics, setMetrics] = useState<HealthMetrics | null>(null);
  const [trends, setTrends] = useState<TrendPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    fetchMetrics();
  }, []);

  const fetchMetrics = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch('/api/v1/dashboard/health', {
        headers: { Authorization: `Bearer ${token}` },
      });
      
      if (response.ok) {
        const data = await response.json();
        setMetrics(data);
        // Generate mock trend data
        setTrends(generateMockTrends(data.overall_health_score));
      }
    } catch (err) {
      console.error('Failed to fetch metrics:', err);
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

  const getScoreBgColor = (score: number) => {
    if (score >= 90) return 'bg-green-50 border-green-200';
    if (score >= 70) return 'bg-yellow-50 border-yellow-200';
    return 'bg-red-50 border-red-200';
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
            
            <button className="btn-ghost">
              <Bell className="w-4 h-4" />
            </button>
            
            <div className="border-l border-slate-200 pl-4 flex items-center gap-2">
              <div className="w-8 h-8 bg-primary-100 rounded-full flex items-center justify-center">
                <User className="w-4 h-4 text-primary-600" />
              </div>
              <button className="btn-ghost p-0">
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* Top Metrics */}
        {metrics && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
            {/* Overall Health Score */}
            <div className={`card-lg border-l-4 ${
              metrics.overall_health_score >= 90 ? 'border-l-green-600' :
              metrics.overall_health_score >= 70 ? 'border-l-yellow-600' :
              'border-l-red-600'
            }`}>
              <div className="flex items-start justify-between mb-4">
                <div>
                  <p className="text-slate-600 text-sm font-medium mb-1">Overall Health</p>
                  <p className={`text-4xl font-bold ${getScoreColor(metrics.overall_health_score)}`}>
                    {Math.round(metrics.overall_health_score)}%
                  </p>
                </div>
                {metrics.overall_health_score >= 90 ? (
                  <CheckCircle className="w-6 h-6 text-green-600" />
                ) : metrics.overall_health_score >= 70 ? (
                  <AlertCircle className="w-6 h-6 text-yellow-600" />
                ) : (
                  <AlertCircle className="w-6 h-6 text-red-600" />
                )}
              </div>
              <p className="text-xs text-slate-500 mt-4 pt-4 border-t border-slate-200">
                Last updated: just now
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
                Requires attention
              </p>
            </div>

            {/* Datasets */}
            <div className="card-lg border-l-4 border-l-blue-600">
              <div className="flex items-start justify-between mb-4">
                <div>
                  <p className="text-slate-600 text-sm font-medium mb-1">Datasets</p>
                  <p className="text-4xl font-bold text-blue-600">{metrics.datasets}</p>
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
                  <p className="text-4xl font-bold text-purple-600">{metrics.quality_rules}</p>
                </div>
                <CheckCircle className="w-6 h-6 text-purple-600" />
              </div>
              <p className="text-xs text-slate-500 mt-4 pt-4 border-t border-slate-200">
                Actively monitored
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
              <div className="flex items-center gap-1 text-green-600 text-sm">
                <TrendingUp className="w-4 h-4" />
                +2.5%
              </div>
            </div>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={trends}>
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
          </div>

          {/* Quality by Dimension */}
          {metrics && (
            <div className="card-lg">
              <h2 className="text-lg font-semibold text-slate-900 mb-6">Quality Dimensions</h2>
              <div className="space-y-4">
                {Object.entries(metrics.dimensions).map(([name, score]) => (
                  <div key={name}>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium text-slate-700 capitalize">
                        {name.replace('_', ' ')}
                      </span>
                      <span className="text-sm font-semibold text-slate-900">
                        {Math.round(score)}%
                      </span>
                    </div>
                    <div className="w-full h-2 bg-slate-200 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-primary-600 rounded-full transition-all"
                        style={{ width: `${Math.min(score, 100)}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Recent Issues */}
        <div className="card-lg">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-lg font-semibold text-slate-900">Recent Issues</h2>
              <p className="text-sm text-slate-600">Critical and high severity issues</p>
            </div>
            <button className="btn-ghost text-sm">View All</button>
          </div>
          
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
                {[
                  { id: 1, issue: 'Missing values detected', dataset: 'Customers', severity: 'High', status: 'Open', detected: '2 hours ago' },
                  { id: 2, issue: 'Format mismatch', dataset: 'Orders', severity: 'Medium', status: 'Open', detected: '4 hours ago' },
                  { id: 3, issue: 'Duplicate records', dataset: 'Products', severity: 'Critical', status: 'In Progress', detected: '6 hours ago' },
                ].map((row) => (
                  <tr key={row.id} className="border-b border-slate-200 hover:bg-slate-50">
                    <td className="py-3 px-4 text-slate-900">{row.issue}</td>
                    <td className="py-3 px-4 text-slate-600">{row.dataset}</td>
                    <td className="py-3 px-4">
                      <span className={`inline-block px-2 py-1 rounded text-xs font-medium ${
                        row.severity === 'Critical' ? 'bg-red-100 text-red-700' :
                        row.severity === 'High' ? 'bg-orange-100 text-orange-700' :
                        'bg-yellow-100 text-yellow-700'
                      }`}>
                        {row.severity}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      <span className={`inline-block px-2 py-1 rounded text-xs font-medium ${
                        row.status === 'Open' ? 'bg-red-100 text-red-700' :
                        'bg-blue-100 text-blue-700'
                      }`}>
                        {row.status}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-slate-500">{row.detected}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}

function generateMockTrends(baseScore: number): TrendPoint[] {
  const trends: TrendPoint[] = [];
  const today = new Date();
  
  for (let i = 29; i >= 0; i--) {
    const date = new Date(today);
    date.setDate(date.getDate() - i);
    const variation = (Math.random() - 0.5) * 10;
    const score = Math.min(100, Math.max(0, baseScore + variation));
    trends.push({
      date: date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      pass_rate: Math.round(score),
    });
  }
  
  return trends;
}
