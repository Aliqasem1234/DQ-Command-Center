import { useState, useEffect } from 'react';
import {
  Search, Filter, Download, Plus, ChevronRight, Database,
  AlertCircle, CheckCircle, Clock, TrendingUp, Users
} from 'lucide-react';

interface Dataset {
  id: string;
  name: string;
  domain: string;
  dataset_type: string;
  row_count: number;
  last_updated: string;
  health_score: number;
  elements_count: number;
  owner: string;
  data_steward?: string;
}

interface DataDomain {
  id: string;
  name: string;
  description: string;
  dataset_count: number;
  health_score: number;
  owner: string;
}

export function DataExplorerModern() {
  const [view, setView] = useState<'domains' | 'datasets'>('domains');
  const [domains, setDomains] = useState<DataDomain[]>([]);
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(true);
  const [selectedDomain, setSelectedDomain] = useState<string | null>(null);

  useEffect(() => {
    fetchData();
  }, [view, selectedDomain]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('access_token');
      
      if (view === 'domains') {
        const response = await fetch('/api/v1/domains', {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (response.ok) {
          const data = await response.json();
          setDomains(data || []);
        }
      } else if (selectedDomain) {
        const response = await fetch(`/api/v1/domains/${selectedDomain}/datasets`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (response.ok) {
          const data = await response.json();
          setDatasets(data || []);
        }
      }
    } catch (err) {
      console.error('Failed to fetch data:', err);
    } finally {
      setLoading(false);
    }
  };

  const getHealthIcon = (score: number) => {
    if (score >= 90) return <CheckCircle className="w-5 h-5 text-green-600" />;
    if (score >= 70) return <AlertCircle className="w-5 h-5 text-yellow-600" />;
    return <AlertCircle className="w-5 h-5 text-red-600" />;
  };

  const getHealthColor = (score: number) => {
    if (score >= 90) return 'text-green-600';
    if (score >= 70) return 'text-yellow-600';
    return 'text-red-600';
  };

  const filteredDomains = domains.filter(d =>
    d.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    d.description.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const filteredDatasets = datasets.filter(d =>
    d.name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="bg-white border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-6 py-6">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h1 className="text-2xl font-bold text-slate-900">Data Explorer</h1>
              <p className="text-slate-600 text-sm mt-1">Browse domains and datasets</p>
            </div>
            <button className="btn-primary flex items-center gap-2">
              <Plus className="w-4 h-4" />
              New Dataset
            </button>
          </div>

          {/* View Tabs */}
          <div className="flex items-center gap-4">
            <button
              onClick={() => {
                setView('domains');
                setSelectedDomain(null);
              }}
              className={`px-4 py-2 font-medium rounded-lg transition-colors ${
                view === 'domains'
                  ? 'bg-primary-100 text-primary-700'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Data Domains
            </button>
            <button
              onClick={() => setView('datasets')}
              className={`px-4 py-2 font-medium rounded-lg transition-colors ${
                view === 'datasets'
                  ? 'bg-primary-100 text-primary-700'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Datasets
            </button>
          </div>
        </div>
      </header>

      {/* Search & Filter Bar */}
      <div className="bg-white border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center gap-4">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <input
                type="text"
                placeholder={view === 'domains' ? 'Search domains...' : 'Search datasets...'}
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="input-base pl-10"
              />
            </div>
            <button className="btn-secondary flex items-center gap-2">
              <Filter className="w-4 h-4" />
              Filter
            </button>
            <button className="btn-secondary flex items-center gap-2">
              <Download className="w-4 h-4" />
              Export
            </button>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-6 py-8">
        {loading ? (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4"></div>
            <p className="text-slate-600">Loading...</p>
          </div>
        ) : view === 'domains' ? (
          /* Domains Grid */
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredDomains.length === 0 ? (
              <div className="col-span-full text-center py-12">
                <Database className="w-12 h-12 text-slate-300 mx-auto mb-4" />
                <p className="text-slate-600">No domains found</p>
              </div>
            ) : (
              filteredDomains.map((domain) => (
                <button
                  key={domain.id}
                  onClick={() => {
                    setView('datasets');
                    setSelectedDomain(domain.id);
                  }}
                  className="card-lg hover:shadow-lg transition-shadow text-left group"
                >
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex items-center gap-3 flex-1">
                      <div className="w-10 h-10 bg-primary-100 rounded-lg flex items-center justify-center">
                        <Database className="w-5 h-5 text-primary-600" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <h3 className="font-semibold text-slate-900 group-hover:text-primary-600 transition-colors truncate">
                          {domain.name}
                        </h3>
                      </div>
                    </div>
                    <ChevronRight className="w-5 h-5 text-slate-400 group-hover:text-primary-600 transition-colors flex-shrink-0" />
                  </div>

                  <p className="text-sm text-slate-600 mb-4 line-clamp-2">
                    {domain.description}
                  </p>

                  <div className="flex items-center justify-between pt-4 border-t border-slate-200">
                    <div className="flex items-center gap-4">
                      <div className="text-center">
                        <p className="text-lg font-semibold text-slate-900">
                          {domain.dataset_count}
                        </p>
                        <p className="text-xs text-slate-500">Datasets</p>
                      </div>
                      <div className="text-center">
                        <p className={`text-lg font-semibold ${getHealthColor(domain.health_score)}`}>
                          {Math.round(domain.health_score)}%
                        </p>
                        <p className="text-xs text-slate-500">Health</p>
                      </div>
                    </div>
                    {getHealthIcon(domain.health_score)}
                  </div>

                  <div className="mt-4 pt-4 border-t border-slate-200 flex items-center gap-2 text-xs text-slate-600">
                    <Users className="w-3 h-3" />
                    Owner: {domain.owner}
                  </div>
                </button>
              ))
            )}
          </div>
        ) : selectedDomain ? (
          /* Datasets Table */
          <div className="space-y-6">
            <button
              onClick={() => setView('domains')}
              className="text-sm text-primary-600 hover:text-primary-700 flex items-center gap-1 mb-6"
            >
              ← Back to Domains
            </button>

            <div className="card-lg overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-200">
                    <th className="text-left py-3 px-4 font-medium text-slate-700">Dataset</th>
                    <th className="text-left py-3 px-4 font-medium text-slate-700">Type</th>
                    <th className="text-left py-3 px-4 font-medium text-slate-700">Records</th>
                    <th className="text-left py-3 px-4 font-medium text-slate-700">Elements</th>
                    <th className="text-left py-3 px-4 font-medium text-slate-700">Health</th>
                    <th className="text-left py-3 px-4 font-medium text-slate-700">Owner</th>
                    <th className="text-left py-3 px-4 font-medium text-slate-700">Updated</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredDatasets.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="text-center py-8 text-slate-500">
                        No datasets found
                      </td>
                    </tr>
                  ) : (
                    filteredDatasets.map((dataset) => (
                      <tr key={dataset.id} className="border-b border-slate-200 hover:bg-slate-50 cursor-pointer">
                        <td className="py-3 px-4 font-medium text-slate-900">{dataset.name}</td>
                        <td className="py-3 px-4 text-slate-600">
                          <span className="inline-block px-2 py-1 bg-slate-100 text-slate-700 rounded text-xs">
                            {dataset.dataset_type}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-slate-600">
                          {dataset.row_count.toLocaleString()}
                        </td>
                        <td className="py-3 px-4 text-slate-600">{dataset.elements_count}</td>
                        <td className="py-3 px-4">
                          <div className="flex items-center gap-2">
                            <span className={`font-medium ${getHealthColor(dataset.health_score)}`}>
                              {Math.round(dataset.health_score)}%
                            </span>
                            {getHealthIcon(dataset.health_score)}
                          </div>
                        </td>
                        <td className="py-3 px-4 text-slate-600">{dataset.owner}</td>
                        <td className="py-3 px-4 text-slate-500 text-xs">
                          {new Date(dataset.last_updated).toLocaleDateString()}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        ) : (
          <div className="text-center py-12">
            <p className="text-slate-600">Select a domain to view datasets</p>
          </div>
        )}
      </div>
    </div>
  );
}
