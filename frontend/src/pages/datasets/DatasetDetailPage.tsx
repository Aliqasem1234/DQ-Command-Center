import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  ArrowLeft, RefreshCw, Download, Upload, Sparkles, AlertCircle, CheckCircle,
  Plus, Trash2, Play,
} from 'lucide-react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';
import { domainService } from '../../services/domainService';
import { datasetFileService } from '../../services/datasetFileService';
import { dashboardService } from '../../services/dashboardService';
import { getErrorMessage } from '../../services/api';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { EmptyState } from '../../components/common/EmptyState';
import type { CleaningOperation, DatasetVersion } from '../../types';

type Tab = 'overview' | 'profile' | 'issues' | 'clean' | 'versions';

export function DatasetDetailPage() {
  const { datasetId } = useParams<{ datasetId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [tab, setTab] = useState<Tab>('overview');
  const [selectedVersionId, setSelectedVersionId] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const { data: dataset, isLoading: datasetLoading } = useQuery({
    queryKey: ['dataset', datasetId],
    queryFn: () => domainService.getDataset(datasetId!),
    enabled: !!datasetId,
  });

  const { data: versions, isLoading: versionsLoading } = useQuery({
    queryKey: ['dataset-versions', datasetId],
    queryFn: () => datasetFileService.listVersions(datasetId!),
    enabled: !!datasetId,
  });

  const latest = versions?.[0];
  const activeVersionId = selectedVersionId || latest?.id;
  const activeVersion = versions?.find((v) => v.id === activeVersionId);

  const { data: issues } = useQuery({
    queryKey: ['dataset-issues', datasetId],
    queryFn: () => dashboardService.getOpenIssues(50, datasetId),
    enabled: !!datasetId,
  });

  const { data: comparison } = useQuery({
    queryKey: ['dataset-quality-comparison', datasetId],
    queryFn: () => datasetFileService.qualityComparison(datasetId!),
    enabled: !!datasetId,
  });

  const invalidateAll = async () => {
    await queryClient.invalidateQueries({ queryKey: ['dataset-versions', datasetId] });
    await queryClient.invalidateQueries({ queryKey: ['dataset-issues', datasetId] });
    await queryClient.invalidateQueries({ queryKey: ['dataset-quality-comparison', datasetId] });
    await queryClient.invalidateQueries({ queryKey: ['dataset', datasetId] });
  };

  const handleScan = async () => {
    if (!activeVersionId) return;
    setBusy(true);
    setActionError(null);
    try {
      await datasetFileService.scan(datasetId!, activeVersionId);
      await invalidateAll();
    } catch (err) {
      setActionError(getErrorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const handleUploadNewVersion = async (file: File) => {
    setBusy(true);
    setActionError(null);
    try {
      await datasetFileService.uploadNewVersion(datasetId!, file);
      await invalidateAll();
    } catch (err) {
      setActionError(getErrorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const handleDownload = async (version: DatasetVersion) => {
    try {
      await datasetFileService.downloadFile(
        datasetId!,
        version.id,
        version.original_filename || `${dataset?.name || 'dataset'}_v${version.version_number}.${version.file_format}`
      );
    } catch (err) {
      setActionError(getErrorMessage(err));
    }
  };

  if (datasetLoading || versionsLoading) return <LoadingSpinner />;
  if (!dataset) return <EmptyState title="Dataset not found" />;

  return (
    <div>
      <button
        onClick={() => navigate('/datasets')}
        className="flex items-center gap-1 text-sm text-slate-600 hover:text-slate-900 mb-4"
      >
        <ArrowLeft size={16} /> Back to Datasets
      </button>

      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">{dataset.name}</h1>
          <p className="text-slate-600 text-sm mt-1">{dataset.description || 'No description'}</p>
        </div>
        <div className="flex items-center gap-3">
          <VersionPicker
            versions={versions || []}
            selectedId={activeVersionId}
            onChange={setSelectedVersionId}
          />
          <button className="btn-ghost flex items-center gap-2" disabled={busy || !activeVersionId} onClick={handleScan}>
            <RefreshCw size={16} className={busy ? 'animate-spin' : ''} />
            Scan
          </button>
          <label className="btn-secondary flex items-center gap-2 cursor-pointer">
            <Upload size={16} />
            New Version
            <input
              type="file"
              accept=".csv,.xlsx,.xls"
              className="hidden"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) handleUploadNewVersion(f);
                e.target.value = '';
              }}
            />
          </label>
        </div>
      </div>

      {actionError && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-800">{actionError}</div>
      )}

      <div className="flex gap-1 border-b border-slate-200 mb-6">
        {(['overview', 'profile', 'issues', 'clean', 'versions'] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium capitalize border-b-2 transition-colors ${
              tab === t ? 'border-primary-600 text-primary-700' : 'border-transparent text-slate-600 hover:text-slate-900'
            }`}
          >
            {t}
            {t === 'issues' && issues && issues.length > 0 && (
              <span className="ml-2 px-1.5 py-0.5 bg-red-100 text-red-700 rounded-full text-xs">{issues.length}</span>
            )}
          </button>
        ))}
      </div>

      {tab === 'overview' && (
        <OverviewTab dataset={dataset} activeVersion={activeVersion} comparison={comparison} />
      )}
      {tab === 'profile' && <ProfileTab datasetId={datasetId!} versionId={activeVersionId} />}
      {tab === 'issues' && <IssuesTab issues={issues || []} />}
      {tab === 'clean' && activeVersionId && (
        <CleanTab
          datasetId={datasetId!}
          versionId={activeVersionId}
          onApplied={async () => {
            await invalidateAll();
            setTab('versions');
          }}
        />
      )}
      {tab === 'versions' && (
        <VersionsTab versions={versions || []} onDownload={handleDownload} />
      )}
    </div>
  );
}

function VersionPicker({
  versions,
  selectedId,
  onChange,
}: {
  versions: DatasetVersion[];
  selectedId: string | undefined;
  onChange: (id: string) => void;
}) {
  if (versions.length === 0) return null;
  return (
    <select
      className="input-base w-auto"
      value={selectedId || ''}
      onChange={(e) => onChange(e.target.value)}
    >
      {versions.map((v) => (
        <option key={v.id} value={v.id}>
          v{v.version_number}{v.is_original ? ' (original)' : ''} — {v.status}
        </option>
      ))}
    </select>
  );
}

function OverviewTab({
  dataset,
  activeVersion,
  comparison,
}: {
  dataset: { row_count: number | null };
  activeVersion: DatasetVersion | undefined;
  comparison: { versions: { version_number: number; quality_score: number | null }[] } | undefined;
}) {
  const score = activeVersion?.quality_score;
  const chartData = (comparison?.versions || [])
    .filter((v) => v.quality_score !== null)
    .map((v) => ({ version: `v${v.version_number}`, score: v.quality_score }));

  return (
    <div>
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <div className="card-lg border-l-4 border-l-blue-600">
          <p className="text-slate-600 text-sm font-medium mb-1">Quality Score</p>
          <p className={`text-4xl font-bold ${score === null || score === undefined ? 'text-slate-400' : score >= 90 ? 'text-green-600' : score >= 70 ? 'text-yellow-600' : 'text-red-600'}`}>
            {score !== null && score !== undefined ? `${Math.round(score)}%` : '—'}
          </p>
          <p className="text-xs text-slate-500 mt-4 pt-4 border-t border-slate-200">
            {activeVersion ? `v${activeVersion.version_number} · ${activeVersion.status}` : 'No version'}
          </p>
        </div>
        <div className="card-lg border-l-4 border-l-purple-600">
          <p className="text-slate-600 text-sm font-medium mb-1">Rows</p>
          <p className="text-4xl font-bold text-purple-600">{activeVersion?.row_count ?? '—'}</p>
        </div>
        <div className="card-lg border-l-4 border-l-orange-600">
          <p className="text-slate-600 text-sm font-medium mb-1">Columns</p>
          <p className="text-4xl font-bold text-orange-600">{activeVersion?.column_count ?? '—'}</p>
        </div>
        <div className="card-lg border-l-4 border-l-green-600">
          <p className="text-slate-600 text-sm font-medium mb-1">File</p>
          <p className="text-sm font-medium text-slate-900 mt-2 truncate">{activeVersion?.original_filename || '—'}</p>
          <p className="text-xs text-slate-500 mt-1">
            {activeVersion?.file_size_bytes ? `${(activeVersion.file_size_bytes / 1024).toFixed(1)} KB` : ''}
          </p>
        </div>
      </div>

      <div className="card-lg">
        <h2 className="text-lg font-semibold text-slate-900 mb-4">Quality Score by Version</h2>
        {chartData.length === 0 ? (
          <EmptyState title="No scans yet" message="Run a scan on a version to see its quality score here." />
        ) : (
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="version" stroke="#94a3b8" />
              <YAxis domain={[0, 100]} stroke="#94a3b8" />
              <Tooltip />
              <Line type="monotone" dataKey="score" stroke="#0ea5e9" strokeWidth={2} name="Quality Score %" />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}

function ProfileTab({ datasetId, versionId }: { datasetId: string; versionId: string | undefined }) {
  const { data: rows, isLoading } = useQuery({
    queryKey: ['dataset-rows-profile', datasetId, versionId],
    queryFn: () => datasetFileService.previewRows(datasetId, versionId!, 1, 5),
    enabled: !!versionId,
  });

  const { data: elements } = useQuery({
    queryKey: ['dataset-elements', datasetId],
    queryFn: async () => {
      const { api } = await import('../../services/api');
      const response = await api.get(`/v1/datasets/${datasetId}/elements`, { params: { page_size: 100 } });
      return response.data as { name: string; data_type: string; nullable: boolean; is_primary_key: boolean }[];
    },
  });

  if (isLoading) return <LoadingSpinner />;

  return (
    <div className="space-y-6">
      <div className="card-lg overflow-hidden">
        <h2 className="text-lg font-semibold text-slate-900 mb-4">Columns</h2>
        {!elements || elements.length === 0 ? (
          <EmptyState title="No profile yet" message="Upload or scan a version to profile its columns." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="border-b border-slate-200 bg-slate-50">
                <tr>
                  <th className="text-left px-4 py-2 text-sm font-semibold text-slate-900">Column</th>
                  <th className="text-left px-4 py-2 text-sm font-semibold text-slate-900">Type</th>
                  <th className="text-left px-4 py-2 text-sm font-semibold text-slate-900">Nullable</th>
                  <th className="text-left px-4 py-2 text-sm font-semibold text-slate-900">Primary Key</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {elements.map((el) => (
                  <tr key={el.name}>
                    <td className="px-4 py-2 text-sm font-medium text-slate-900">{el.name}</td>
                    <td className="px-4 py-2 text-sm text-slate-600 capitalize">{el.data_type}</td>
                    <td className="px-4 py-2 text-sm text-slate-600">{el.nullable ? 'Yes' : 'No'}</td>
                    <td className="px-4 py-2 text-sm text-slate-600">{el.is_primary_key ? 'Yes' : 'No'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="card-lg overflow-hidden">
        <h2 className="text-lg font-semibold text-slate-900 mb-4">Sample Rows</h2>
        {!rows || rows.rows.length === 0 ? (
          <EmptyState title="No data" />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="border-b border-slate-200 bg-slate-50">
                <tr>
                  {rows.columns.map((c) => (
                    <th key={c} className="text-left px-3 py-2 font-semibold text-slate-900">{c}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {rows.rows.map((row, i) => (
                  <tr key={i}>
                    {rows.columns.map((c) => (
                      <td key={c} className="px-3 py-2 text-slate-700">{String(row[c] ?? '')}</td>
                    ))}
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

function IssuesTab({ issues }: { issues: { id: string; description: string | null; severity: string; status: string; dataset_name: string | null; detected_at: string }[] }) {
  if (issues.length === 0) {
    return (
      <EmptyState
        icon={<CheckCircle size={40} className="text-green-600" />}
        title="No open issues"
        message="Run a scan to check this dataset for quality problems."
      />
    );
  }
  return (
    <div className="card-lg overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="border-b border-slate-200 bg-slate-50">
            <tr>
              <th className="text-left px-6 py-3 text-sm font-semibold text-slate-900">Issue</th>
              <th className="text-left px-6 py-3 text-sm font-semibold text-slate-900">Severity</th>
              <th className="text-left px-6 py-3 text-sm font-semibold text-slate-900">Detected</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200">
            {issues.map((issue) => (
              <tr key={issue.id} className="hover:bg-slate-50">
                <td className="px-6 py-4 text-sm text-slate-900">{issue.description}</td>
                <td className="px-6 py-4 text-sm">
                  <span className={`px-2 py-1 rounded-full text-xs font-medium capitalize ${
                    issue.severity === 'critical' ? 'bg-red-100 text-red-800' :
                    issue.severity === 'high' ? 'bg-orange-100 text-orange-800' :
                    issue.severity === 'medium' ? 'bg-yellow-100 text-yellow-800' : 'bg-slate-100 text-slate-700'
                  }`}>
                    {issue.severity}
                  </span>
                </td>
                <td className="px-6 py-4 text-sm text-slate-600">{new Date(issue.detected_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

const OPERATION_LABELS: Record<CleaningOperation['type'], string> = {
  trim_whitespace: 'Trim whitespace',
  collapse_whitespace: 'Collapse multiple spaces',
  standardize_case: 'Standardize text case',
  normalize_dates: 'Normalize date format',
  remove_duplicate_rows: 'Remove exact duplicate rows',
  fill_missing: 'Fill missing values',
};

function CleanTab({
  datasetId,
  versionId,
  onApplied,
}: {
  datasetId: string;
  versionId: string;
  onApplied: () => void;
}) {
  const [operations, setOperations] = useState<CleaningOperation[]>([{ type: 'trim_whitespace', columns: 'all' }]);
  const [preview, setPreview] = useState<Awaited<ReturnType<typeof datasetFileService.previewCleaning>> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const addOperation = () => setOperations([...operations, { type: 'trim_whitespace', columns: 'all' }]);
  const removeOperation = (i: number) => setOperations(operations.filter((_, idx) => idx !== i));
  const updateOperation = (i: number, patch: Partial<CleaningOperation>) =>
    setOperations(operations.map((op, idx) => (idx === i ? { ...op, ...patch } : op)));

  const handlePreview = async () => {
    setLoading(true);
    setError(null);
    setPreview(null);
    try {
      const result = await datasetFileService.previewCleaning(datasetId, versionId, operations);
      setPreview(result);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const handleApply = async () => {
    setLoading(true);
    setError(null);
    try {
      await datasetFileService.applyCleaning(datasetId, versionId, operations);
      onApplied();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="card-lg">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-slate-900 flex items-center gap-2">
            <Sparkles size={18} className="text-primary-600" /> Cleaning Operations
          </h2>
          <button className="btn-ghost flex items-center gap-1 text-sm" onClick={addOperation}>
            <Plus size={16} /> Add operation
          </button>
        </div>

        <div className="space-y-3">
          {operations.map((op, i) => (
            <div key={i} className="flex items-center gap-3 p-3 bg-slate-50 rounded-lg">
              <select
                className="input-base"
                value={op.type}
                onChange={(e) => updateOperation(i, { type: e.target.value as CleaningOperation['type'] })}
              >
                {Object.entries(OPERATION_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>{label}</option>
                ))}
              </select>

              {(op.type === 'standardize_case' || op.type === 'normalize_dates' || op.type === 'fill_missing') && (
                <input
                  className="input-base"
                  placeholder="Column name"
                  value={op.column || ''}
                  onChange={(e) => updateOperation(i, { column: e.target.value })}
                />
              )}

              {op.type === 'standardize_case' && (
                <select className="input-base" value={op.case || 'lower'} onChange={(e) => updateOperation(i, { case: e.target.value as CleaningOperation['case'] })}>
                  <option value="lower">lowercase</option>
                  <option value="upper">UPPERCASE</option>
                  <option value="title">Title Case</option>
                </select>
              )}

              {op.type === 'fill_missing' && (
                <>
                  <select className="input-base" value={op.strategy || 'fill_value'} onChange={(e) => updateOperation(i, { strategy: e.target.value as CleaningOperation['strategy'] })}>
                    <option value="fill_value">Fixed value</option>
                    <option value="fill_mean">Mean</option>
                    <option value="fill_median">Median</option>
                    <option value="fill_mode">Most common value</option>
                    <option value="drop_row">Drop the row</option>
                  </select>
                  {op.strategy === 'fill_value' && (
                    <input
                      className="input-base"
                      placeholder="Value"
                      value={op.value || ''}
                      onChange={(e) => updateOperation(i, { value: e.target.value })}
                    />
                  )}
                </>
              )}

              <button className="p-2 text-slate-500 hover:text-red-600" onClick={() => removeOperation(i)}>
                <Trash2 size={16} />
              </button>
            </div>
          ))}
        </div>

        {error && <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-800">{error}</div>}

        <div className="flex gap-3 mt-6">
          <button className="btn-secondary flex items-center gap-2" onClick={handlePreview} disabled={loading}>
            <Play size={16} /> Preview
          </button>
          <button className="btn-primary flex items-center gap-2" onClick={handleApply} disabled={loading || !preview}>
            <CheckCircle size={16} /> Apply (creates new version)
          </button>
        </div>
      </div>

      {preview && (
        <div className="card-lg">
          <h3 className="text-md font-semibold text-slate-900 mb-3">Preview</h3>
          <div className="flex gap-6 mb-4 text-sm">
            <span><strong>{preview.rows_changed}</strong> rows would change</span>
            <span><strong>{preview.values_changed}</strong> values would change</span>
            <span><strong>{preview.result_row_count}</strong> rows in result (from {preview.original_row_count})</span>
          </div>
          {preview.sample_changes.length === 0 ? (
            <EmptyState title="No changes detected" message="These operations wouldn't change anything in this version." />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="border-b border-slate-200 bg-slate-50">
                  <tr>
                    <th className="text-left px-3 py-2 font-semibold text-slate-900">Before</th>
                    <th className="text-left px-3 py-2 font-semibold text-slate-900">After</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200">
                  {preview.sample_changes.map((s, i) => (
                    <tr key={i}>
                      <td className="px-3 py-2 text-red-700 font-mono text-xs">{JSON.stringify(s.before)}</td>
                      <td className="px-3 py-2 text-green-700 font-mono text-xs">{JSON.stringify(s.after)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function VersionsTab({
  versions,
  onDownload,
}: {
  versions: DatasetVersion[];
  onDownload: (v: DatasetVersion) => void;
}) {
  if (versions.length === 0) return <EmptyState title="No versions" />;
  return (
    <div className="card-lg overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="border-b border-slate-200 bg-slate-50">
            <tr>
              <th className="text-left px-6 py-3 text-sm font-semibold text-slate-900">Version</th>
              <th className="text-left px-6 py-3 text-sm font-semibold text-slate-900">Rows</th>
              <th className="text-left px-6 py-3 text-sm font-semibold text-slate-900">Quality</th>
              <th className="text-left px-6 py-3 text-sm font-semibold text-slate-900">Changes</th>
              <th className="text-left px-6 py-3 text-sm font-semibold text-slate-900">Created</th>
              <th className="text-right px-6 py-3 text-sm font-semibold text-slate-900">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200">
            {versions.map((v) => (
              <tr key={v.id} className="hover:bg-slate-50">
                <td className="px-6 py-4 text-sm font-medium text-slate-900">
                  v{v.version_number} {v.is_original && <span className="text-xs text-slate-500">(original)</span>}
                </td>
                <td className="px-6 py-4 text-sm text-slate-600">{v.row_count ?? '—'}</td>
                <td className="px-6 py-4 text-sm text-slate-600">
                  {v.quality_score !== null ? `${Math.round(v.quality_score)}%` : (
                    <span className="text-slate-400 flex items-center gap-1"><AlertCircle size={14} /> not scanned</span>
                  )}
                </td>
                <td className="px-6 py-4 text-sm text-slate-600">
                  {v.rows_changed !== null ? `${v.rows_changed} rows, ${v.values_changed} values` : '—'}
                </td>
                <td className="px-6 py-4 text-sm text-slate-600">{new Date(v.created_at).toLocaleString()}</td>
                <td className="px-6 py-4 text-right">
                  <button className="p-1 text-slate-600 hover:text-primary-700 hover:bg-slate-100 rounded" onClick={() => onDownload(v)} title="Download">
                    <Download size={16} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
