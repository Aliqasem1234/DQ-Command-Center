import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  ArrowLeft, RefreshCw, Download, Upload, Sparkles, AlertCircle, CheckCircle,
  Plus, Trash2, Play, Pencil, Check, X as CloseIcon,
} from 'lucide-react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';
import { domainService } from '../../services/domainService';
import { datasetFileService } from '../../services/datasetFileService';
import { dashboardService } from '../../services/dashboardService';
import { api, getErrorMessage } from '../../services/api';
import { useThemeStore } from '../../store/themeStore';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { EmptyState } from '../../components/common/EmptyState';
import type { CleaningOperation, DatasetVersion } from '../../types';

type Tab = 'overview' | 'profile' | 'issues' | 'clean' | 'versions';

export function DatasetDetailPage() {
  const { t } = useTranslation();
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

  const { data: domains } = useQuery({
    queryKey: ['domains'],
    queryFn: () => domainService.list(1, 50),
  });

  const handleDomainChange = async (domainId: string | null) => {
    setActionError(null);
    try {
      await domainService.updateDatasetDomain(datasetId!, domainId);
      await queryClient.invalidateQueries({ queryKey: ['dataset', datasetId] });
      await queryClient.invalidateQueries({ queryKey: ['all-datasets'] });
    } catch (err) {
      setActionError(getErrorMessage(err));
    }
  };

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
  if (!dataset) return <EmptyState title={t('datasets.datasetNotFound')} />;

  return (
    <div>
      <button
        onClick={() => navigate('/datasets')}
        className="flex items-center gap-1 text-sm text-slate-600 hover:text-slate-900 mb-4"
      >
        <ArrowLeft size={16} /> {t('datasets.backToDatasets')}
      </button>

      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">{dataset.name}</h1>
          <p className="text-slate-600 text-sm mt-1">{dataset.description || t('datasets.noDescription')}</p>
          <DomainBadge
            domainId={dataset.domain_id}
            domains={domains ?? []}
            onChange={handleDomainChange}
          />
        </div>
        <div className="flex items-center gap-3">
          <VersionPicker
            versions={versions || []}
            selectedId={activeVersionId}
            onChange={setSelectedVersionId}
          />
          <button className="btn-ghost flex items-center gap-2" disabled={busy || !activeVersionId} onClick={handleScan}>
            <RefreshCw size={16} className={busy ? 'animate-spin' : ''} />
            {t('datasets.scan')}
          </button>
          <label className="btn-secondary flex items-center gap-2 cursor-pointer">
            <Upload size={16} />
            {t('datasets.newVersion')}
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
        {(['overview', 'profile', 'issues', 'clean', 'versions'] as Tab[]).map((tabKey) => (
          <button
            key={tabKey}
            onClick={() => setTab(tabKey)}
            className={`px-4 py-2 text-sm font-medium capitalize border-b-2 transition-colors ${
              tab === tabKey ? 'border-primary-600 text-primary-700' : 'border-transparent text-slate-600 hover:text-slate-900'
            }`}
          >
            {t(TAB_LABEL_KEY[tabKey])}
            {tabKey === 'issues' && issues && issues.length > 0 && (
              <span className="badge badge-error ml-2">{issues.length}</span>
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

function DomainBadge({
  domainId,
  domains,
  onChange,
}: {
  domainId: string | null;
  domains: { id: string; name: string }[];
  onChange: (domainId: string | null) => Promise<void>;
}) {
  const { t } = useTranslation();
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState(domainId ?? '');
  const [saving, setSaving] = useState(false);

  const domainName = domainId ? domains.find((d) => d.id === domainId)?.name : null;

  if (editing) {
    return (
      <div className="flex items-center gap-1.5 mt-2">
        <select className="input-base w-auto py-1 text-sm" value={value} onChange={(e) => setValue(e.target.value)} autoFocus>
          <option value="">{t('datasets.noDomainOption')}</option>
          {domains.map((d) => (
            <option key={d.id} value={d.id}>{d.name}</option>
          ))}
        </select>
        <button
          className="icon-btn !p-1.5 text-green-600"
          disabled={saving}
          onClick={async () => {
            setSaving(true);
            await onChange(value || null);
            setSaving(false);
            setEditing(false);
          }}
          title={t('common.save')}
        >
          <Check size={16} />
        </button>
        <button className="icon-btn !p-1.5" onClick={() => setEditing(false)} title={t('common.cancel')}>
          <CloseIcon size={16} />
        </button>
      </div>
    );
  }

  return (
    <button
      onClick={() => { setValue(domainId ?? ''); setEditing(true); }}
      className="flex items-center gap-1.5 mt-2 text-xs text-slate-500 hover:text-slate-800 dark:hover:text-slate-200 group"
    >
      <span className="border border-slate-200 dark:border-slate-700 rounded-md px-2 py-0.5">
        {domainName ?? t('datasets.noDomainOption')}
      </span>
      <Pencil size={12} className="opacity-0 group-hover:opacity-100 transition-opacity" />
    </button>
  );
}

const TAB_LABEL_KEY: Record<Tab, string> = {
  overview: 'datasets.tabOverview',
  profile: 'datasets.tabProfile',
  issues: 'datasets.tabIssues',
  clean: 'datasets.tabClean',
  versions: 'datasets.tabVersions',
};

function VersionPicker({
  versions,
  selectedId,
  onChange,
}: {
  versions: DatasetVersion[];
  selectedId: string | undefined;
  onChange: (id: string) => void;
}) {
  const { t } = useTranslation();
  if (versions.length === 0) return null;
  return (
    <select
      className="input-base w-auto"
      value={selectedId || ''}
      onChange={(e) => onChange(e.target.value)}
    >
      {versions.map((v) => (
        <option key={v.id} value={v.id}>
          v{v.version_number}{v.is_original ? ` ${t('datasets.original')}` : ''} — {t(`datasets.versionStatus.${v.status}`, { defaultValue: v.status })}
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
  const { t } = useTranslation();
  const { mode } = useThemeStore();
  const isDark = mode === 'dark';
  const axisColor = isDark ? '#64748b' : '#94a3b8';
  const gridColor = isDark ? '#334155' : '#e2e8f0';
  const tooltipStyle = isDark
    ? { backgroundColor: '#1e293b', border: '1px solid #334155', color: '#f1f5f9' }
    : { backgroundColor: '#f8fafc', border: '1px solid #e2e8f0', color: '#0f172a' };
  const score = activeVersion?.quality_score;
  const chartData = (comparison?.versions || [])
    .filter((v) => v.quality_score !== null)
    .map((v) => ({ version: `v${v.version_number}`, score: v.quality_score }));

  return (
    <div>
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <div className="card-lg border-l-4 border-l-blue-600">
          <p className="text-slate-600 text-sm font-medium mb-1">{t('datasets.qualityScore')}</p>
          <p className={`text-4xl font-bold ${score === null || score === undefined ? 'text-slate-400' : score >= 90 ? 'text-green-600' : score >= 70 ? 'text-yellow-600' : 'text-red-600'}`}>
            {score !== null && score !== undefined ? `${Math.round(score)}%` : '—'}
          </p>
          <p className="text-xs text-slate-500 mt-4 pt-4 border-t border-slate-200">
            {activeVersion ? `v${activeVersion.version_number} · ${t(`datasets.versionStatus.${activeVersion.status}`, { defaultValue: activeVersion.status })}` : t('datasets.noVersion')}
          </p>
        </div>
        <div className="card-lg border-l-4 border-l-purple-600">
          <p className="text-slate-600 text-sm font-medium mb-1 capitalize">{t('datasets.rows')}</p>
          <p className="text-4xl font-bold text-purple-600">{activeVersion?.row_count ?? '—'}</p>
        </div>
        <div className="card-lg border-l-4 border-l-orange-600">
          <p className="text-slate-600 text-sm font-medium mb-1">{t('datasets.columns')}</p>
          <p className="text-4xl font-bold text-orange-600">{activeVersion?.column_count ?? '—'}</p>
        </div>
        <div className="card-lg border-l-4 border-l-green-600">
          <p className="text-slate-600 text-sm font-medium mb-1">{t('datasets.file')}</p>
          <p className="text-sm font-medium text-slate-900 mt-2 truncate">{activeVersion?.original_filename || '—'}</p>
          <p className="text-xs text-slate-500 mt-1">
            {activeVersion?.file_size_bytes ? `${(activeVersion.file_size_bytes / 1024).toFixed(1)} KB` : ''}
          </p>
        </div>
      </div>

      <div className="card-lg">
        <h2 className="text-lg font-semibold text-slate-900 mb-4">{t('datasets.qualityScoreByVersion')}</h2>
        {chartData.length === 0 ? (
          <EmptyState title={t('datasets.noScansTitle')} message={t('datasets.noScansMessage')} />
        ) : (
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
              <XAxis dataKey="version" stroke={axisColor} />
              <YAxis domain={[0, 100]} stroke={axisColor} />
              <Tooltip contentStyle={tooltipStyle} />
              <Line type="monotone" dataKey="score" stroke="#0ea5e9" strokeWidth={2} name={t('datasets.qualityScoreLegend')} />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}

function ProfileTab({ datasetId, versionId }: { datasetId: string; versionId: string | undefined }) {
  const { t } = useTranslation();
  const { data: rows, isLoading } = useQuery({
    queryKey: ['dataset-rows-profile', datasetId, versionId],
    queryFn: () => datasetFileService.previewRows(datasetId, versionId!, 1, 5),
    enabled: !!versionId,
  });

  const { data: elements } = useQuery({
    queryKey: ['dataset-elements', datasetId],
    queryFn: async () => {
      const response = await api.get(`/v1/datasets/${datasetId}/elements`, { params: { page_size: 100 } });
      return response.data as { name: string; data_type: string; nullable: boolean; is_primary_key: boolean }[];
    },
  });

  if (isLoading) return <LoadingSpinner />;

  return (
    <div className="space-y-6">
      <div className="card-lg overflow-hidden">
        <h2 className="text-lg font-semibold text-slate-900 mb-4">{t('datasets.columns')}</h2>
        {!elements || elements.length === 0 ? (
          <EmptyState title={t('datasets.noProfileTitle')} message={t('datasets.noProfileMessage')} />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="border-b border-slate-200 bg-slate-50">
                <tr>
                  <th className="text-left px-4 py-2 text-sm font-semibold text-slate-900">{t('datasets.columnHeader')}</th>
                  <th className="text-left px-4 py-2 text-sm font-semibold text-slate-900">{t('common.type')}</th>
                  <th className="text-left px-4 py-2 text-sm font-semibold text-slate-900">{t('datasets.nullableHeader')}</th>
                  <th className="text-left px-4 py-2 text-sm font-semibold text-slate-900">{t('datasets.primaryKeyHeader')}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {elements.map((el) => (
                  <tr key={el.name}>
                    <td className="px-4 py-2 text-sm font-medium text-slate-900">{el.name}</td>
                    <td className="px-4 py-2 text-sm text-slate-600 capitalize">{el.data_type}</td>
                    <td className="px-4 py-2 text-sm text-slate-600">{el.nullable ? t('common.yes') : t('common.no')}</td>
                    <td className="px-4 py-2 text-sm text-slate-600">{el.is_primary_key ? t('common.yes') : t('common.no')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="card-lg overflow-hidden">
        <h2 className="text-lg font-semibold text-slate-900 mb-4">{t('datasets.sampleRows')}</h2>
        {!rows || rows.rows.length === 0 ? (
          <EmptyState title={t('datasets.noDataTitle')} />
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
  const { t } = useTranslation();
  if (issues.length === 0) {
    return (
      <EmptyState
        icon={<CheckCircle size={40} className="text-green-600" />}
        title={t('datasets.noOpenIssuesTitle')}
        message={t('datasets.noOpenIssuesMessage')}
      />
    );
  }
  return (
    <div className="card-lg overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="border-b border-slate-200 bg-slate-50">
            <tr>
              <th className="text-left px-6 py-3 text-sm font-semibold text-slate-900">{t('dashboard.issueColumn')}</th>
              <th className="text-left px-6 py-3 text-sm font-semibold text-slate-900">{t('dataQuality.severity')}</th>
              <th className="text-left px-6 py-3 text-sm font-semibold text-slate-900">{t('dashboard.detectedColumn')}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200">
            {issues.map((issue) => (
              <tr key={issue.id} className="hover:bg-slate-50">
                <td className="px-6 py-4 text-sm text-slate-900">{issue.description}</td>
                <td className="px-6 py-4 text-sm">
                  <span className={`badge capitalize ${
                    issue.severity === 'critical' ? 'badge-error' :
                    issue.severity === 'high' ? 'badge-warning' :
                    issue.severity === 'medium' ? 'badge-warning' : 'badge-info'
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

const OPERATION_LABEL_KEY: Record<CleaningOperation['type'], string> = {
  trim_whitespace: 'datasets.operations.trim_whitespace',
  collapse_whitespace: 'datasets.operations.collapse_whitespace',
  standardize_case: 'datasets.operations.standardize_case',
  normalize_dates: 'datasets.operations.normalize_dates',
  remove_duplicate_rows: 'datasets.operations.remove_duplicate_rows',
  fill_missing: 'datasets.operations.fill_missing',
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
  const { t } = useTranslation();
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
            <Sparkles size={18} className="text-primary-600" /> {t('datasets.cleaningOperations')}
          </h2>
          <button className="btn-ghost flex items-center gap-1 text-sm" onClick={addOperation}>
            <Plus size={16} /> {t('datasets.addOperation')}
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
                {Object.entries(OPERATION_LABEL_KEY).map(([value, key]) => (
                  <option key={value} value={value}>{t(key)}</option>
                ))}
              </select>

              {(op.type === 'standardize_case' || op.type === 'normalize_dates' || op.type === 'fill_missing') && (
                <input
                  className="input-base"
                  placeholder={t('datasets.columnNamePlaceholder')}
                  value={op.column || ''}
                  onChange={(e) => updateOperation(i, { column: e.target.value })}
                />
              )}

              {op.type === 'standardize_case' && (
                <select className="input-base" value={op.case || 'lower'} onChange={(e) => updateOperation(i, { case: e.target.value as CleaningOperation['case'] })}>
                  <option value="lower">{t('datasets.lowercase')}</option>
                  <option value="upper">{t('datasets.uppercase')}</option>
                  <option value="title">{t('datasets.titleCase')}</option>
                </select>
              )}

              {op.type === 'fill_missing' && (
                <>
                  <select className="input-base" value={op.strategy || 'fill_value'} onChange={(e) => updateOperation(i, { strategy: e.target.value as CleaningOperation['strategy'] })}>
                    <option value="fill_value">{t('datasets.fixedValue')}</option>
                    <option value="fill_mean">{t('datasets.mean')}</option>
                    <option value="fill_median">{t('datasets.median')}</option>
                    <option value="fill_mode">{t('datasets.mostCommon')}</option>
                    <option value="drop_row">{t('datasets.dropRow')}</option>
                  </select>
                  {op.strategy === 'fill_value' && (
                    <input
                      className="input-base"
                      placeholder={t('datasets.valuePlaceholder')}
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

        {error && <div className="alert alert-error mt-4">{error}</div>}

        <div className="flex gap-3 mt-6">
          <button className="btn-secondary flex items-center gap-2" onClick={handlePreview} disabled={loading}>
            <Play size={16} /> {t('datasets.preview')}
          </button>
          <button className="btn-primary flex items-center gap-2" onClick={handleApply} disabled={loading || !preview}>
            <CheckCircle size={16} /> {t('datasets.applyCreatesVersion')}
          </button>
        </div>
      </div>

      {preview && (
        <div className="card-lg">
          <h3 className="text-md font-semibold text-slate-900 mb-3">{t('datasets.previewHeading')}</h3>
          <div className="flex gap-6 mb-4 text-sm">
            <span><strong>{preview.rows_changed}</strong> {t('datasets.rowsWouldChange')}</span>
            <span><strong>{preview.values_changed}</strong> {t('datasets.valuesWouldChange')}</span>
            <span><strong>{preview.result_row_count}</strong> {t('datasets.rowsInResultFrom', { original: preview.original_row_count })}</span>
          </div>
          {preview.sample_changes.length === 0 ? (
            <EmptyState title={t('datasets.noChangesTitle')} message={t('datasets.noChangesMessage')} />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="border-b border-slate-200 bg-slate-50">
                  <tr>
                    <th className="text-left px-3 py-2 font-semibold text-slate-900">{t('datasets.before')}</th>
                    <th className="text-left px-3 py-2 font-semibold text-slate-900">{t('datasets.after')}</th>
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
  const { t } = useTranslation();
  if (versions.length === 0) return <EmptyState title={t('datasets.noVersionsTitle')} />;
  return (
    <div className="card-lg overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="border-b border-slate-200 bg-slate-50">
            <tr>
              <th className="text-left px-6 py-3 text-sm font-semibold text-slate-900">{t('datasets.versionHeader')}</th>
              <th className="text-left px-6 py-3 text-sm font-semibold text-slate-900 capitalize">{t('datasets.rows')}</th>
              <th className="text-left px-6 py-3 text-sm font-semibold text-slate-900">{t('datasets.qualityScore')}</th>
              <th className="text-left px-6 py-3 text-sm font-semibold text-slate-900">{t('datasets.changesHeader')}</th>
              <th className="text-left px-6 py-3 text-sm font-semibold text-slate-900">{t('datasets.createdHeader')}</th>
              <th className="text-right px-6 py-3 text-sm font-semibold text-slate-900">{t('common.actions')}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200">
            {versions.map((v) => (
              <tr key={v.id} className="hover:bg-slate-50">
                <td className="px-6 py-4 text-sm font-medium text-slate-900">
                  v{v.version_number} {v.is_original && <span className="text-xs text-slate-500">{t('datasets.original')}</span>}
                </td>
                <td className="px-6 py-4 text-sm text-slate-600">{v.row_count ?? '—'}</td>
                <td className="px-6 py-4 text-sm text-slate-600">
                  {v.quality_score !== null ? `${Math.round(v.quality_score)}%` : (
                    <span className="text-slate-400 flex items-center gap-1"><AlertCircle size={14} /> {t('common.notScanned')}</span>
                  )}
                </td>
                <td className="px-6 py-4 text-sm text-slate-600">
                  {v.rows_changed !== null ? `${v.rows_changed} rows, ${v.values_changed} values` : '—'}
                </td>
                <td className="px-6 py-4 text-sm text-slate-600">{new Date(v.created_at).toLocaleString()}</td>
                <td className="px-6 py-4 text-right">
                  <button className="p-1 text-slate-600 hover:text-primary-700 hover:bg-slate-100 rounded" onClick={() => onDownload(v)} title={t('common.download')} aria-label={t('common.download')}>
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
