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
import { CHART_AXIS_COLOR, CHART_GRID_COLOR, CHART_TOOLTIP_STYLE } from '../../theme/chart';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { EmptyState } from '../../components/common/EmptyState';
import type { CleaningOperation, CleaningPreview, DatasetVersion } from '../../types';
import { usePermission } from '../../hooks/usePermission';
import { PERMISSIONS } from '../../auth/permissions';
import { ConfirmDialog } from '../../components/common/ConfirmDialog';
import { useAuthStore } from '../../store/authStore';

type Tab = 'overview' | 'profile' | 'issues' | 'clean' | 'versions';

export function DatasetDetailPage() {
  const { t } = useTranslation();
  const { datasetId } = useParams<{ datasetId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const canManage = usePermission(PERMISSIONS.datasetsManage);
  const currentUser = useAuthStore((s) => s.user);
  const [confirmDelete, setConfirmDelete] = useState(false);
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

  const handleRestore = async (version: DatasetVersion) => {
    setActionError(null);
    try {
      const restored = await datasetFileService.restoreVersion(datasetId!, version.id);
      await invalidateAll();
      setSelectedVersionId(restored.id);
    } catch (err) {
      setActionError(getErrorMessage(err));
    }
  };

  const handleDelete = async () => {
    setConfirmDelete(false);
    setActionError(null);
    try {
      await domainService.deleteDataset(datasetId!);
      queryClient.removeQueries({ queryKey: ['dataset', datasetId] });
      await queryClient.invalidateQueries({ queryKey: ['all-datasets'] });
      navigate('/datasets');
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
            readOnly={!canManage}
          />
        </div>
        <div className="flex items-center gap-3">
          <VersionPicker
            versions={versions || []}
            selectedId={activeVersionId}
            onChange={setSelectedVersionId}
          />
          {canManage && (
          <>
          <button className="btn-ghost flex items-center gap-2" disabled={busy || !activeVersionId} onClick={handleScan}>
            <RefreshCw size={16} className={busy ? 'animate-spin' : ''} />
            {t('datasets.scan')}
          </button>
          <label className="btn-secondary flex items-center gap-2 cursor-pointer">
            <Upload size={16} />
            {t('datasets.newVersion')}
            <input
              type="file"
              accept=".csv,.xlsx"
              className="hidden"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) handleUploadNewVersion(f);
                e.target.value = '';
              }}
            />
          </label>
          </>
          )}
          {/* Only the owner may delete (stewards/shared users can't; the API enforces it). */}
          {canManage && (currentUser?.is_super_admin || dataset.data_owner_id === currentUser?.id) && (
            <button
              type="button"
              className="btn-ghost flex items-center gap-2 text-red-600 dark:text-red-400"
              onClick={() => setConfirmDelete(true)}
            >
              <Trash2 size={16} />
              {t('datasets.deleteDataset')}
            </button>
          )}
        </div>
      </div>

      {actionError && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-800">{actionError}</div>
      )}

      <div className="flex gap-1 border-b border-slate-200 mb-6">
        {(['overview', 'profile', 'issues', 'clean', 'versions'] as Tab[])
          .filter((tabKey) => tabKey !== 'clean' || canManage)
          .map((tabKey) => (
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
      {tab === 'clean' && canManage && activeVersionId && (
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
        <VersionsTab versions={versions || []} onDownload={handleDownload} onRestore={handleRestore} canManage={canManage} />
      )}

      <ConfirmDialog
        open={confirmDelete}
        title={t('datasets.deleteDataset')}
        message={t('datasets.deleteDatasetConfirm', { name: dataset.name })}
        confirmText={t('common.delete')}
        onConfirm={handleDelete}
        onCancel={() => setConfirmDelete(false)}
      />
    </div>
  );
}

function DomainBadge({
  domainId,
  domains,
  onChange,
  readOnly = false,
}: {
  domainId: string | null;
  domains: { id: string; name: string }[];
  onChange: (domainId: string | null) => Promise<void>;
  readOnly?: boolean;
}) {
  const { t } = useTranslation();
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState(domainId ?? '');
  const [saving, setSaving] = useState(false);

  const domainName = domainId ? domains.find((d) => d.id === domainId)?.name : null;

  if (readOnly) {
    return (
      <span className="inline-block mt-2 text-xs text-slate-500 border border-slate-200 dark:border-slate-700 rounded-md px-2 py-0.5">
        {domainName ?? t('datasets.noDomainOption')}
      </span>
    );
  }

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
  const axisColor = CHART_AXIS_COLOR;
  const gridColor = CHART_GRID_COLOR;
  const tooltipStyle = CHART_TOOLTIP_STYLE;
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
  remove_control_characters: 'datasets.operations.remove_control_characters',
  standardize_case: 'datasets.operations.standardize_case',
  normalize_dates: 'datasets.operations.normalize_dates',
  convert_type: 'datasets.operations.convert_type',
  map_values: 'datasets.operations.map_values',
  remove_duplicate_rows: 'datasets.operations.remove_duplicate_rows',
  fill_missing: 'datasets.operations.fill_missing',
};

// Operations the backend refuses to run on "all columns" (see
// data_cleaning_service): the user must pick columns.
const NEEDS_COLUMNS: CleaningOperation['type'][] = ['normalize_dates', 'convert_type', 'map_values', 'fill_missing'];

function defaultOperation(type: CleaningOperation['type']): CleaningOperation {
  if (NEEDS_COLUMNS.includes(type)) return { type, columns: [] };
  if (type === 'remove_duplicate_rows') return { type, columns: 'all', keep: 'first' };
  return { type, columns: 'all' };
}

function parseMapping(text: string): Record<string, string> {
  // One "from = to" pair per line.
  const mapping: Record<string, string> = {};
  for (const line of text.split('\n')) {
    const idx = line.indexOf('=');
    if (idx > 0) mapping[line.slice(0, idx).trim()] = line.slice(idx + 1).trim();
  }
  return mapping;
}

function ColumnPicker({
  columns,
  value,
  allowAll,
  onChange,
}: {
  columns: string[];
  value: CleaningOperation['columns'];
  allowAll: boolean;
  onChange: (v: CleaningOperation['columns']) => void;
}) {
  const { t } = useTranslation();
  const selected = value === 'all' || value === undefined ? [] : value;
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      {allowAll && (
        <button
          type="button"
          className={`badge ${value === 'all' ? 'badge-info' : ''} cursor-pointer`}
          onClick={() => onChange('all')}
        >
          {t('datasets.allColumns')}
        </button>
      )}
      {columns.map((c) => {
        const on = selected.includes(c);
        return (
          <button
            key={c}
            type="button"
            className={`badge cursor-pointer ${on ? 'badge-info' : ''}`}
            aria-pressed={on}
            onClick={() => onChange(on ? selected.filter((x) => x !== c) : [...selected, c])}
          >
            {c}
          </button>
        );
      })}
    </div>
  );
}

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
  const [operations, setOperations] = useState<CleaningOperation[]>([defaultOperation('trim_whitespace')]);
  const [mappingText, setMappingText] = useState<Record<number, string>>({});
  const [preview, setPreview] = useState<CleaningPreview | null>(null);
  const [previewedFor, setPreviewedFor] = useState<string | null>(null);
  const [confirmRemoval, setConfirmRemoval] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const { data: rowPage } = useQuery({
    queryKey: ['dataset-columns', datasetId, versionId],
    queryFn: () => datasetFileService.previewRows(datasetId, versionId, 1, 1),
  });
  const columns = rowPage?.columns ?? [];

  // The preview is only valid for exactly the operations it was computed
  // for; any edit invalidates it so "apply" can't run something unseen.
  const requestOps = operations.map((op, i) =>
    op.type === 'map_values' ? { ...op, mapping: parseMapping(mappingText[i] ?? '') } : op,
  );
  const signature = JSON.stringify(requestOps);
  const previewIsCurrent = preview !== null && previewedFor === signature;

  const update = (i: number, patch: Partial<CleaningOperation>) =>
    setOperations(operations.map((op, idx) => (idx === i ? { ...op, ...patch } : op)));

  const handlePreview = async () => {
    setLoading(true);
    setError(null);
    setPreview(null);
    try {
      const result = await datasetFileService.previewCleaning(datasetId, versionId, requestOps);
      setPreview(result);
      setPreviewedFor(signature);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const apply = async () => {
    setConfirmRemoval(false);
    setLoading(true);
    setError(null);
    try {
      await datasetFileService.applyCleaning(datasetId, versionId, requestOps);
      onApplied();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const handleApply = () => {
    if (preview?.removes_rows) setConfirmRemoval(true);
    else void apply();
  };

  const scoreText = (v: number | null) => (v === null ? '—' : `${Math.round(v * 10) / 10}%`);

  return (
    <div className="space-y-6">
      <div className="card-lg">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-lg font-semibold text-slate-900 flex items-center gap-2">
            <Sparkles size={18} className="text-primary-600" /> {t('datasets.cleaningOperations')}
          </h2>
          <button className="btn-ghost flex items-center gap-1 text-sm" onClick={() => setOperations([...operations, defaultOperation('trim_whitespace')])}>
            <Plus size={16} /> {t('datasets.addOperation')}
          </button>
        </div>
        <p className="text-sm text-slate-500 mb-4">{t('datasets.cleaningIntro')}</p>

        <div className="space-y-3">
          {operations.map((op, i) => (
            <div key={i} className="p-3 bg-slate-50 rounded-lg space-y-3">
              <div className="flex items-center gap-3">
                <span className="text-xs font-semibold text-slate-500 w-5">{i + 1}.</span>
                <select
                  className="input-base"
                  aria-label={t('datasets.operationType')}
                  value={op.type}
                  onChange={(e) => update(i, defaultOperation(e.target.value as CleaningOperation['type']))}
                >
                  {Object.entries(OPERATION_LABEL_KEY).map(([value, key]) => (
                    <option key={value} value={value}>{t(key)}</option>
                  ))}
                </select>
                <button className="p-2 text-slate-500 hover:text-red-600" onClick={() => setOperations(operations.filter((_, idx) => idx !== i))} aria-label={t('common.delete')}>
                  <Trash2 size={16} />
                </button>
              </div>
              <p className="text-xs text-slate-500 pl-8">{t(`datasets.operationHelp.${op.type}`)}</p>

              <div className="pl-8 space-y-2">
                <ColumnPicker
                  columns={columns}
                  value={op.columns}
                  allowAll={!NEEDS_COLUMNS.includes(op.type)}
                  onChange={(v) => update(i, { columns: v })}
                />

                {op.type === 'standardize_case' && (
                  <select className="input-base w-auto" value={op.case || 'lower'} onChange={(e) => update(i, { case: e.target.value as CleaningOperation['case'] })}>
                    <option value="lower">{t('datasets.lowercase')}</option>
                    <option value="upper">{t('datasets.uppercase')}</option>
                    <option value="title">{t('datasets.titleCase')}</option>
                  </select>
                )}

                {op.type === 'normalize_dates' && (
                  <div className="flex flex-wrap gap-2">
                    <input className="input-base w-48" placeholder={t('datasets.sourceFormatPlaceholder')} value={op.source_format || ''}
                      onChange={(e) => update(i, { source_format: e.target.value || undefined })} />
                    <select className="input-base w-auto" value={op.day_first === undefined ? '' : String(op.day_first)}
                      onChange={(e) => update(i, { day_first: e.target.value === '' ? undefined : e.target.value === 'true' })}>
                      <option value="">{t('datasets.dayFirstUnknown')}</option>
                      <option value="true">{t('datasets.dayFirstTrue')}</option>
                      <option value="false">{t('datasets.dayFirstFalse')}</option>
                    </select>
                  </div>
                )}

                {op.type === 'convert_type' && (
                  <div className="flex flex-wrap gap-2">
                    <select className="input-base w-auto" value={op.target || ''} onChange={(e) => update(i, { target: e.target.value as CleaningOperation['target'] })}>
                      <option value="" disabled>{t('datasets.chooseTargetType')}</option>
                      <option value="integer">{t('datasets.typeInteger')}</option>
                      <option value="decimal">{t('datasets.typeDecimal')}</option>
                      <option value="boolean">{t('datasets.typeBoolean')}</option>
                    </select>
                    {op.target === 'decimal' || op.target === 'integer' ? (
                      <select className="input-base w-auto" value={op.decimal_separator || '.'} onChange={(e) => update(i, { decimal_separator: e.target.value as '.' | ',' })}>
                        <option value=".">{t('datasets.decimalPoint')}</option>
                        <option value=",">{t('datasets.decimalComma')}</option>
                      </select>
                    ) : null}
                    <select className="input-base w-auto" value={op.on_invalid || 'keep'} onChange={(e) => update(i, { on_invalid: e.target.value as 'keep' | 'set_missing' })}>
                      <option value="keep">{t('datasets.invalidKeep')}</option>
                      <option value="set_missing">{t('datasets.invalidSetMissing')}</option>
                    </select>
                  </div>
                )}

                {op.type === 'map_values' && (
                  <textarea className="input-base font-mono text-xs" rows={3} placeholder={t('datasets.mappingPlaceholder')}
                    value={mappingText[i] ?? ''} onChange={(e) => setMappingText({ ...mappingText, [i]: e.target.value })} />
                )}

                {op.type === 'remove_duplicate_rows' && (
                  <select className="input-base w-auto" value={op.keep || 'first'} onChange={(e) => update(i, { keep: e.target.value as 'first' | 'last' })}>
                    <option value="first">{t('datasets.keepFirst')}</option>
                    <option value="last">{t('datasets.keepLast')}</option>
                  </select>
                )}

                {op.type === 'fill_missing' && (
                  <div className="flex flex-wrap gap-2">
                    <select className="input-base w-auto" value={op.strategy || 'fill_value'} onChange={(e) => update(i, { strategy: e.target.value as CleaningOperation['strategy'] })}>
                      <option value="fill_value">{t('datasets.fixedValue')}</option>
                      <option value="fill_mean">{t('datasets.mean')}</option>
                      <option value="fill_median">{t('datasets.median')}</option>
                      <option value="fill_mode">{t('datasets.mostCommon')}</option>
                      <option value="drop_row">{t('datasets.dropRow')}</option>
                    </select>
                    {(op.strategy ?? 'fill_value') === 'fill_value' && (
                      <input className="input-base w-48" placeholder={t('datasets.valuePlaceholder')} value={op.value || ''}
                        onChange={(e) => update(i, { value: e.target.value })} />
                    )}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>

        {error && <div className="alert alert-error mt-4 whitespace-pre-line">{error}</div>}

        <div className="flex flex-wrap items-center gap-3 mt-6">
          <button className="btn-secondary flex items-center gap-2" onClick={handlePreview} disabled={loading || operations.length === 0}>
            <Play size={16} /> {t('datasets.preview')}
          </button>
          <button className="btn-primary flex items-center gap-2" onClick={handleApply} disabled={loading || !previewIsCurrent}>
            <CheckCircle size={16} /> {t('datasets.applyCreatesVersion')}
          </button>
          {preview && !previewIsCurrent && <span className="text-xs text-yellow-600">{t('datasets.previewOutdated')}</span>}
        </div>
      </div>

      {preview && previewIsCurrent && (
        <div className="card-lg space-y-4">
          <h3 className="text-md font-semibold text-slate-900">{t('datasets.previewHeading')}</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
            <div><p className="text-slate-500">{t('datasets.previewRowsModified')}</p><p className="text-xl font-semibold text-slate-900">{preview.rows_modified}</p></div>
            <div><p className="text-slate-500">{t('datasets.previewRowsRemoved')}</p><p className={`text-xl font-semibold ${preview.rows_removed ? 'text-red-600' : 'text-slate-900'}`}>{preview.rows_removed}</p></div>
            <div><p className="text-slate-500">{t('datasets.previewValuesChanged')}</p><p className="text-xl font-semibold text-slate-900">{preview.values_changed}</p></div>
            <div><p className="text-slate-500">{t('datasets.previewQuality')}</p><p className="text-xl font-semibold text-slate-900">{scoreText(preview.quality_score_before)} → {scoreText(preview.quality_score_after)}</p></div>
          </div>
          <p className="text-xs text-slate-500">
            {t('datasets.previewRowsSummary', { original: preview.original_row_count, result: preview.result_row_count })}
            {' · '}{t('datasets.previewDuplicates', { before: preview.exact_duplicates_before, after: preview.exact_duplicates_after })}
            {preview.potential_duplicates_after > 0 && <> {' · '}<span className="text-yellow-600">{t('datasets.previewPotentialDuplicates', { count: preview.potential_duplicates_after })}</span></>}
          </p>
          {preview.rows_removed > 0 && <div className="alert alert-warning text-sm">{t('datasets.previewScoreNote')}</div>}
          {Object.keys(preview.changed_columns).length > 0 && (
            <p className="text-xs text-slate-500">{t('datasets.previewChangedColumns')}: {Object.entries(preview.changed_columns).map(([c, n]) => `${c} (${n})`).join(', ')}</p>
          )}
          {preview.operations_report.some((r) => r.skipped > 0) && (
            <div className="alert alert-warning text-sm space-y-1">
              {preview.operations_report.map((r, i) => r.skipped > 0 && (
                <div key={i}>
                  <strong>{i + 1}. {t(OPERATION_LABEL_KEY[r.type as CleaningOperation['type']] ?? r.type)}</strong>: {t('datasets.previewSkipped', { count: r.skipped })}
                  {' '}{r.skipped_examples.map((e) => `${e.column}="${e.value}" (${t(`datasets.skipReason.${e.reason}`, { defaultValue: e.reason })})`).join(', ')}
                </div>
              ))}
            </div>
          )}
          {preview.sample_changes.length === 0 ? (
            <EmptyState title={t('datasets.noChangesTitle')} message={t('datasets.noChangesMessage')} />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="border-b border-slate-200 bg-slate-50">
                  <tr>
                    <th className="text-left px-3 py-2 font-semibold text-slate-900">{t('datasets.rowNumber')}</th>
                    <th className="text-left px-3 py-2 font-semibold text-slate-900">{t('datasets.before')}</th>
                    <th className="text-left px-3 py-2 font-semibold text-slate-900">{t('datasets.after')}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200">
                  {preview.sample_changes.map((s, i) => (
                    <tr key={i}>
                      <td className="px-3 py-2 text-slate-500">{s.row}</td>
                      <td className="px-3 py-2 text-red-700 font-mono text-xs">{JSON.stringify(s.before)}</td>
                      <td className="px-3 py-2 font-mono text-xs">
                        {s.after === null ? <span className="text-red-600">{t('datasets.rowRemoved')}</span> : <span className="text-green-700">{JSON.stringify(s.after)}</span>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      <ConfirmDialog
        open={confirmRemoval}
        title={t('datasets.confirmRemovalTitle')}
        message={t('datasets.confirmRemovalMessage', { count: preview?.rows_removed ?? 0 })}
        confirmText={t('datasets.applyCreatesVersion')}
        onConfirm={() => void apply()}
        onCancel={() => setConfirmRemoval(false)}
      />
    </div>
  );
}

function describeOperations(v: DatasetVersion, t: (k: string, o?: Record<string, unknown>) => string): string {
  if (v.is_original) return t('datasets.historyUploaded');
  const ops = v.cleaning_operations ?? [];
  if (ops.length === 1 && (ops[0] as { type: string }).type === 'restore') {
    return t('datasets.historyRestored', { version: (ops[0] as { from_version?: number }).from_version });
  }
  return ops.map((op) => t(OPERATION_LABEL_KEY[op.type as CleaningOperation['type']] ?? String(op.type))).join(' → ');
}

function VersionsTab({
  versions,
  onDownload,
  onRestore,
  canManage,
}: {
  versions: DatasetVersion[];
  onDownload: (v: DatasetVersion) => void;
  onRestore: (v: DatasetVersion) => void;
  canManage: boolean;
}) {
  const { t } = useTranslation();
  const [restoreTarget, setRestoreTarget] = useState<DatasetVersion | null>(null);
  if (versions.length === 0) return <EmptyState title={t('datasets.noVersionsTitle')} />;
  const latest = Math.max(...versions.map((v) => v.version_number));
  return (
    <div className="card-lg overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="border-b border-slate-200 bg-slate-50">
            <tr>
              <th className="text-left px-6 py-3 text-sm font-semibold text-slate-900">{t('datasets.versionHeader')}</th>
              <th className="text-left px-6 py-3 text-sm font-semibold text-slate-900">{t('datasets.historyHeader')}</th>
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
                <td className="px-6 py-4 text-sm text-slate-600">{describeOperations(v, t)}</td>
                <td className="px-6 py-4 text-sm text-slate-600">{v.row_count ?? '—'}</td>
                <td className="px-6 py-4 text-sm text-slate-600">
                  {v.quality_score !== null ? `${Math.round(v.quality_score)}%` : (
                    <span className="text-slate-400 flex items-center gap-1"><AlertCircle size={14} /> {t('common.notScanned')}</span>
                  )}
                </td>
                <td className="px-6 py-4 text-sm text-slate-600">
                  {v.rows_changed !== null && !v.is_original ? t('datasets.changesSummary', { rows: v.rows_changed, values: v.values_changed ?? 0 }) : '—'}
                </td>
                <td className="px-6 py-4 text-sm text-slate-600">
                  {new Date(v.created_at).toLocaleString()}
                  {v.created_by_name && <span className="block text-xs text-slate-400">{v.created_by_name}</span>}
                </td>
                <td className="px-6 py-4 text-right whitespace-nowrap">
                  {canManage && v.version_number !== latest && (
                    <button className="p-1 mr-1 text-slate-600 hover:text-primary-700 hover:bg-slate-100 rounded" onClick={() => setRestoreTarget(v)}
                      title={t('datasets.restoreVersion')} aria-label={t('datasets.restoreVersion')}>
                      <RefreshCw size={16} />
                    </button>
                  )}
                  <button className="p-1 text-slate-600 hover:text-primary-700 hover:bg-slate-100 rounded" onClick={() => onDownload(v)} title={t('common.download')} aria-label={t('common.download')}>
                    <Download size={16} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <ConfirmDialog
        open={restoreTarget !== null}
        title={t('datasets.restoreVersion')}
        message={t('datasets.restoreConfirm', { version: restoreTarget?.version_number })}
        confirmText={t('datasets.restoreVersion')}
        onConfirm={() => { if (restoreTarget) onRestore(restoreTarget); setRestoreTarget(null); }}
        onCancel={() => setRestoreTarget(null)}
      />
    </div>
  );
}
