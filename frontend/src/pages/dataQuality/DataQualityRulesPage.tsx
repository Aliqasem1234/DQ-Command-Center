import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Plus, Trash2, Edit2, Play } from 'lucide-react';
import { dataQualityService } from '../../services/dataQualityService';
import { domainService } from '../../services/domainService';
import { api, getErrorMessage } from '../../services/api';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { EmptyState } from '../../components/common/EmptyState';
import { ConfirmDialog } from '../../components/common/ConfirmDialog';
import {
  DataQualityDimension,
  RuleSeverity,
  RuleStatus,
  type DataQualityRule,
} from '../../types/dataQuality';
import { usePermission } from '../../hooks/usePermission';
import { PERMISSIONS } from '../../auth/permissions';

const DIMENSIONS = Object.values(DataQualityDimension);

type RuleForm = {
  name: string;
  dimension: DataQualityDimension;
  rule_type: string;
  severity: RuleSeverity;
  status?: RuleStatus;
  dataset_id?: string;
  data_source?: string;
  target_field?: string;
  rule_definition?: Record<string, unknown>;
};
const SEVERITIES = Object.values(RuleSeverity);

export default function DataQualityRulesPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const canManage = usePermission(PERMISSIONS.qualityManage);

  const { data, isLoading, error } = useQuery({
    queryKey: ['data-quality-rules'],
    queryFn: () => dataQualityService.listRules(undefined, undefined, 1, 100),
  });
  // The user's own datasets: names for the table, choices for new rules.
  const { data: datasets } = useQuery({
    queryKey: ['all-datasets'],
    queryFn: () => domainService.listAllDatasets(),
  });
  const datasetName = new Map((datasets ?? []).map((d) => [d.id, d.name]));

  const [editing, setEditing] = useState<DataQualityRule | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<DataQualityRule | null>(null);
  const [running, setRunning] = useState<string | null>(null);
  const [runMessage, setRunMessage] = useState<string | null>(null);

  const handleRun = async (rule: DataQualityRule) => {
    setRunning(rule.id);
    setFormError(null);
    setRunMessage(null);
    try {
      const r = await dataQualityService.runRule(rule.id);
      setRunMessage(
        r.status === 'error'
          ? t('dataQuality.runError', { name: rule.name, error: r.error })
          : r.status === 'passed'
            ? t('dataQuality.runPassed', { name: rule.name, checked: r.records_checked })
            : t('dataQuality.runFailed', { name: rule.name, failed: r.records_failed, checked: r.records_checked, rows: r.failing_rows.slice(0, 10).join(', ') }),
      );
      await queryClient.invalidateQueries({ queryKey: ['data-quality-rules'] });
    } catch (err) {
      setFormError(getErrorMessage(err));
    } finally {
      setRunning(null);
    }
  };
  const [formError, setFormError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const closeForm = () => {
    setIsCreating(false);
    setEditing(null);
    setFormError(null);
  };

  const handleSave = async (form: RuleForm) => {
    setSaving(true);
    setFormError(null);
    try {
      if (editing) {
        // A rule's dataset is fixed when it is created.
        const { dataset_id: _ignored, ...changes } = form;
        await dataQualityService.updateRule(editing.id, changes);
      } else {
        await dataQualityService.createRule(form);
      }
      await queryClient.invalidateQueries({ queryKey: ['data-quality-rules'] });
      closeForm();
    } catch (err) {
      setFormError(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await dataQualityService.deleteRule(deleteTarget.id);
      await queryClient.invalidateQueries({ queryKey: ['data-quality-rules'] });
    } catch (err) {
      setFormError(getErrorMessage(err));
    } finally {
      setDeleteTarget(null);
    }
  };

  const rules = data?.items ?? [];

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">{t('dataQuality.rules')}</h1>
        {canManage && (
          <button className="flex items-center gap-2 btn-primary" onClick={() => setIsCreating(true)}>
            <Plus size={18} />
            {t('common.add')}
          </button>
        )}
      </div>

      <p className="text-sm text-slate-500 -mt-4 mb-6">{t('dataQuality.rulesIntro')}</p>

      {formError && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-800">
          {formError}
        </div>
      )}
      {runMessage && <div className="alert alert-info mb-4 text-sm" role="status">{runMessage}</div>}

      <div className="card-lg overflow-hidden">
        {isLoading ? (
          <LoadingSpinner />
        ) : error ? (
          <div className="p-6 text-sm text-red-700">{getErrorMessage(error)}</div>
        ) : rules.length === 0 ? (
          <EmptyState title={t('common.noData')} />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr>
                  <th>{t('common.name')}</th>
                  <th>{t('dataQuality.dataSource')}</th>
                  <th>{t('dataQuality.dimensions')}</th>
                  <th>{t('dataQuality.severity')}</th>
                  <th>{t('common.status')}</th>
                  <th>{t('dataQuality.lastRun')}</th>
                  <th className="text-right">{t('common.actions')}</th>
                </tr>
              </thead>
              <tbody>
                {rules.map((rule) => (
                  <tr key={rule.id}>
                    <td className="font-medium text-slate-900">{rule.name}</td>
                    <td className="text-slate-500">
                      {(rule.dataset_id && datasetName.get(rule.dataset_id)) || rule.data_source || '—'}
                    </td>
                    <td className="text-slate-600">{t(`dimensions.${rule.dimension}`, { defaultValue: rule.dimension })}</td>
                    <td>
                      <span
                        className={`badge capitalize ${
                          rule.severity === 'critical' ? 'badge-error' :
                          rule.severity === 'high' ? 'badge-warning' :
                          'badge-warning'
                        }`}
                      >
                        <span className="badge-dot" />
                        {t(`dataQuality.severityLevel.${rule.severity}`, { defaultValue: rule.severity })}
                      </span>
                    </td>
                    <td>
                      <span
                        className={`badge capitalize ${rule.status === 'active' ? 'badge-success' : 'badge-info'}`}
                      >
                        <span className="badge-dot" />
                        {t(`dataQuality.statusValue.${rule.status}`, { defaultValue: rule.status })}
                      </span>
                    </td>
                    <td className="text-sm">
                      {!rule.executable ? (
                        <span className="text-slate-400" title={t('dataQuality.definitionOnlyHelp')}>{t('dataQuality.definitionOnly')}</span>
                      ) : !rule.last_result_status ? (
                        <span className="text-slate-400">{t('dataQuality.neverRun')}</span>
                      ) : rule.last_result_status === 'passed' ? (
                        <span className="text-green-600">{t('dataQuality.resultPassed')}</span>
                      ) : rule.last_result_status === 'error' ? (
                        <span className="text-red-600">{t('dataQuality.resultError')}</span>
                      ) : (
                        <span className="text-yellow-600">{t('dataQuality.resultFailed', { failed: rule.last_records_failed, checked: rule.last_records_checked })}</span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-right">
                      {canManage && <div className="flex items-center justify-end gap-2">
                        {rule.executable && (
                          <button
                            className="p-1 text-slate-600 hover:text-primary-700 hover:bg-slate-100 rounded disabled:opacity-40"
                            onClick={() => handleRun(rule)}
                            disabled={running !== null}
                            title={t('dataQuality.runRule')}
                            aria-label={t('dataQuality.runRule')}
                          >
                            <Play size={16} className={running === rule.id ? 'animate-pulse' : ''} />
                          </button>
                        )}
                        {rule.rule_definition?.source !== 'auto_discovery' && (
                        <button
                          className="p-1 text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded"
                          onClick={() => setEditing(rule)}
                          title={t('common.edit')}
                        >
                          <Edit2 size={16} />
                        </button>
                        )}
                        <button
                          className="p-1 text-slate-600 hover:text-red-600 hover:bg-red-50 rounded"
                          onClick={() => setDeleteTarget(rule)}
                          title={t('common.delete')}
                        >
                          <Trash2 size={16} />
                        </button>
                      </div>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {(isCreating || editing) && (
        <RuleFormModal initial={editing} datasets={datasets ?? []} saving={saving} onCancel={closeForm} onSave={handleSave} />
      )}

      <ConfirmDialog
        open={!!deleteTarget}
        title={t('common.delete')}
        message={t('dataQuality.deleteConfirm')}
        onConfirm={handleDelete}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  );
}

// Rule types the backend can execute (app/services/rule_engine.py). Any
// other type is stored as a documentation-only definition.
const EXECUTABLE_TYPES = ['not_null', 'unique', 'email_format', 'numeric_range', 'allowed_values', 'date_range'] as const;
type ExecutableType = (typeof EXECUTABLE_TYPES)[number];
const DEFAULT_DIMENSION: Record<ExecutableType, DataQualityDimension> = {
  not_null: DataQualityDimension.COMPLETENESS,
  unique: DataQualityDimension.UNIQUENESS,
  email_format: DataQualityDimension.VALIDITY,
  numeric_range: DataQualityDimension.VALIDITY,
  allowed_values: DataQualityDimension.VALIDITY,
  date_range: DataQualityDimension.VALIDITY,
};
const isExecutableType = (v: string): v is ExecutableType => (EXECUTABLE_TYPES as readonly string[]).includes(v);

function RuleFormModal({
  initial,
  datasets,
  saving,
  onCancel,
  onSave,
}: {
  initial: DataQualityRule | null;
  datasets: { id: string; name: string }[];
  saving: boolean;
  onCancel: () => void;
  onSave: (form: RuleForm) => void;
}) {
  const { t } = useTranslation();
  const def = (initial?.rule_definition ?? {}) as Record<string, unknown>;
  const [name, setName] = useState(initial?.name ?? '');
  const [ruleType, setRuleType] = useState(initial?.rule_type ?? 'not_null');
  const [customType, setCustomType] = useState(initial && !isExecutableType(initial.rule_type) ? initial.rule_type : '');
  const [dimension, setDimension] = useState<DataQualityDimension>(initial?.dimension ?? DataQualityDimension.COMPLETENESS);
  const [severity, setSeverity] = useState<RuleSeverity>(initial?.severity ?? RuleSeverity.MEDIUM);
  const [datasetId, setDatasetId] = useState(initial?.dataset_id ?? '');
  const [targetField, setTargetField] = useState(initial?.target_field ?? '');
  const [min, setMin] = useState(def.min !== undefined ? String(def.min) : '');
  const [max, setMax] = useState(def.max !== undefined ? String(def.max) : '');
  const [values, setValues] = useState(Array.isArray(def.values) ? (def.values as string[]).join('\n') : '');
  const [caseSensitive, setCaseSensitive] = useState(Boolean(def.case_sensitive ?? false));
  const [minDate, setMinDate] = useState((def.min_date as string) ?? '');
  const [maxDate, setMaxDate] = useState((def.max_date as string) ?? '');
  const [dayFirst, setDayFirst] = useState(def.day_first === undefined ? '' : String(def.day_first));
  const [localError, setLocalError] = useState<string | null>(null);

  const executable = isExecutableType(ruleType);
  const { data: elements } = useQuery({
    queryKey: ['dataset-elements', datasetId],
    queryFn: async () => (await api.get<{ name: string }[]>(`/v1/datasets/${datasetId}/elements`, { params: { page_size: 100 } })).data,
    enabled: Boolean(datasetId),
  });

  const buildDefinition = (): Record<string, unknown> | undefined => {
    if (!executable) return undefined;
    if (ruleType === 'numeric_range') {
      const d: Record<string, unknown> = {};
      if (min !== '') d.min = Number(min);
      if (max !== '') d.max = Number(max);
      return d;
    }
    if (ruleType === 'allowed_values') {
      return { values: values.split('\n').map((v) => v.trim()).filter(Boolean), case_sensitive: caseSensitive };
    }
    if (ruleType === 'date_range') {
      const d: Record<string, unknown> = {};
      if (minDate) d.min_date = minDate;
      if (maxDate) d.max_date = maxDate;
      if (dayFirst !== '') d.day_first = dayFirst === 'true';
      return d;
    }
    if (ruleType === 'unique') return { case_sensitive: caseSensitive };
    return {};
  };

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    setLocalError(null);
    const type = executable ? ruleType : customType.trim();
    if (!type) {
      setLocalError(t('dataQuality.ruleTypeRequired'));
      return;
    }
    if (executable && (!datasetId || !targetField)) {
      setLocalError(t('dataQuality.executableNeedsTarget'));
      return;
    }
    onSave({
      name,
      dimension,
      rule_type: type,
      severity,
      dataset_id: datasetId || undefined,
      target_field: targetField || undefined,
      rule_definition: buildDefinition(),
      // Executable rules start active so scans run them; plain definitions
      // stay drafts.
      ...(initial ? {} : { status: executable ? RuleStatus.ACTIVE : RuleStatus.DRAFT }),
    });
  };

  return (
    <div className="fixed inset-0 bg-slate-950/60 backdrop-blur-sm flex items-center justify-center z-50 p-4" role="dialog" aria-modal="true">
      <div className="bg-white rounded-xl shadow-2xl max-w-lg w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6 border-b border-slate-200">
          <h2 className="text-lg font-semibold text-slate-900">{initial ? t('dataQuality.editRule') : t('dataQuality.newRule')}</h2>
        </div>
        <form onSubmit={submit}>
          <div className="p-6 space-y-4">
            <div>
              <label htmlFor="rule-name" className="block text-sm font-medium text-slate-700 mb-1">{t('common.name')}</label>
              <input id="rule-name" className="input-base" value={name} onChange={(e) => setName(e.target.value)} required autoFocus />
            </div>

            <div>
              <label htmlFor="rule-type" className="block text-sm font-medium text-slate-700 mb-1">{t('dataQuality.ruleType')}</label>
              <select
                id="rule-type"
                className="input-base"
                value={executable ? ruleType : 'other'}
                onChange={(e) => {
                  const v = e.target.value;
                  setRuleType(v);
                  if (isExecutableType(v)) setDimension(DEFAULT_DIMENSION[v]);
                }}
              >
                {EXECUTABLE_TYPES.map((v) => <option key={v} value={v}>{t(`dataQuality.ruleTypes.${v}`)}</option>)}
                <option value="other">{t('dataQuality.ruleTypes.other')}</option>
              </select>
              <p className="text-xs text-slate-500 mt-1">{t(executable ? `dataQuality.ruleTypeHelp.${ruleType}` : 'dataQuality.ruleTypeHelp.other')}</p>
              {!executable && (
                <input className="input-base mt-2" placeholder={t('dataQuality.customTypePlaceholder')} value={customType} onChange={(e) => setCustomType(e.target.value)} />
              )}
            </div>

            <div>
              <label htmlFor="rule-dataset" className="block text-sm font-medium text-slate-700 mb-1">{t('common.dataset')}</label>
              <select id="rule-dataset" className="input-base" value={datasetId} disabled={Boolean(initial)}
                onChange={(e) => { setDatasetId(e.target.value); setTargetField(''); }}>
                <option value="">{t('dataQuality.noDataset')}</option>
                {datasets.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
              </select>
            </div>

            <div>
              <label htmlFor="rule-column" className="block text-sm font-medium text-slate-700 mb-1">{t('dataQuality.targetField')}</label>
              {elements && elements.length > 0 ? (
                <select id="rule-column" className="input-base" value={targetField} onChange={(e) => setTargetField(e.target.value)}>
                  <option value="">{t('dataQuality.chooseColumn')}</option>
                  {elements.map((el) => <option key={el.name} value={el.name}>{el.name}</option>)}
                </select>
              ) : (
                <input id="rule-column" className="input-base" value={targetField} onChange={(e) => setTargetField(e.target.value)} />
              )}
            </div>

            {ruleType === 'numeric_range' && (
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label htmlFor="rule-min" className="block text-sm font-medium text-slate-700 mb-1">{t('dataQuality.minValue')}</label>
                  <input id="rule-min" type="number" step="any" className="input-base" value={min} onChange={(e) => setMin(e.target.value)} />
                </div>
                <div>
                  <label htmlFor="rule-max" className="block text-sm font-medium text-slate-700 mb-1">{t('dataQuality.maxValue')}</label>
                  <input id="rule-max" type="number" step="any" className="input-base" value={max} onChange={(e) => setMax(e.target.value)} />
                </div>
              </div>
            )}
            {ruleType === 'allowed_values' && (
              <div>
                <label htmlFor="rule-values" className="block text-sm font-medium text-slate-700 mb-1">{t('dataQuality.allowedValues')}</label>
                <textarea id="rule-values" className="input-base" rows={4} value={values} onChange={(e) => setValues(e.target.value)} placeholder={t('dataQuality.allowedValuesPlaceholder')} />
              </div>
            )}
            {(ruleType === 'allowed_values' || ruleType === 'unique') && (
              <label className="flex items-center gap-2 text-sm text-slate-700">
                <input type="checkbox" checked={caseSensitive} onChange={(e) => setCaseSensitive(e.target.checked)} />
                {t('dataQuality.caseSensitive')}
              </label>
            )}
            {ruleType === 'date_range' && (
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label htmlFor="rule-min-date" className="block text-sm font-medium text-slate-700 mb-1">{t('dataQuality.minDate')}</label>
                  <input id="rule-min-date" type="date" className="input-base" value={minDate} onChange={(e) => setMinDate(e.target.value)} />
                </div>
                <div>
                  <label htmlFor="rule-max-date" className="block text-sm font-medium text-slate-700 mb-1">{t('dataQuality.maxDate')}</label>
                  <input id="rule-max-date" type="date" className="input-base" value={maxDate} onChange={(e) => setMaxDate(e.target.value)} />
                </div>
                <select className="input-base col-span-2" value={dayFirst} onChange={(e) => setDayFirst(e.target.value)} aria-label={t('datasets.dayFirstUnknown')}>
                  <option value="">{t('datasets.dayFirstUnknown')}</option>
                  <option value="true">{t('datasets.dayFirstTrue')}</option>
                  <option value="false">{t('datasets.dayFirstFalse')}</option>
                </select>
              </div>
            )}

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">{t('dataQuality.dimensions')}</label>
                <select className="input-base" value={dimension} onChange={(e) => setDimension(e.target.value as DataQualityDimension)}>
                  {DIMENSIONS.map((d) => <option key={d} value={d}>{t(`dimensions.${d}`, { defaultValue: d })}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">{t('dataQuality.severity')}</label>
                <select className="input-base" value={severity} onChange={(e) => setSeverity(e.target.value as RuleSeverity)}>
                  {SEVERITIES.map((s) => <option key={s} value={s}>{t(`dataQuality.severityLevel.${s}`, { defaultValue: s })}</option>)}
                </select>
              </div>
            </div>
            {localError && <div className="alert alert-error text-sm">{localError}</div>}
          </div>
          <div className="p-6 border-t border-slate-200 flex justify-end gap-3">
            <button type="button" onClick={onCancel} className="px-4 py-2 text-slate-700 border border-slate-300 rounded-lg hover:bg-slate-50 transition-colors font-medium">
              {t('common.cancel')}
            </button>
            <button type="submit" disabled={saving} className="btn-primary">
              {saving ? t('common.loading') : t('common.save')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
