import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Plus, Trash2, Edit2 } from 'lucide-react';
import { dataQualityService } from '../../services/dataQualityService';
import { getErrorMessage } from '../../services/api';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { EmptyState } from '../../components/common/EmptyState';
import { ConfirmDialog } from '../../components/common/ConfirmDialog';
import {
  DataQualityDimension,
  RuleSeverity,
  type DataQualityRule,
} from '../../types/dataQuality';

const DIMENSIONS = Object.values(DataQualityDimension);
const SEVERITIES = Object.values(RuleSeverity);

export default function DataQualityRulesPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const { data, isLoading, error } = useQuery({
    queryKey: ['data-quality-rules'],
    queryFn: () => dataQualityService.listRules(undefined, undefined, 1, 100),
  });

  const [editing, setEditing] = useState<DataQualityRule | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<DataQualityRule | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const closeForm = () => {
    setIsCreating(false);
    setEditing(null);
    setFormError(null);
  };

  const handleSave = async (form: {
    name: string;
    dimension: DataQualityDimension;
    rule_type: string;
    severity: RuleSeverity;
    data_source?: string;
    target_field?: string;
  }) => {
    setSaving(true);
    setFormError(null);
    try {
      if (editing) {
        await dataQualityService.updateRule(editing.id, form);
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
        <button className="flex items-center gap-2 btn-primary" onClick={() => setIsCreating(true)}>
          <Plus size={18} />
          {t('common.add')}
        </button>
      </div>

      {formError && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-800">
          {formError}
        </div>
      )}

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
                  <th className="text-right">{t('common.actions')}</th>
                </tr>
              </thead>
              <tbody>
                {rules.map((rule) => (
                  <tr key={rule.id}>
                    <td className="font-medium text-slate-900">{rule.name}</td>
                    <td className="text-slate-500">{rule.data_source || '—'}</td>
                    <td className="text-slate-600 capitalize">{rule.dimension}</td>
                    <td>
                      <span
                        className={`badge capitalize ${
                          rule.severity === 'critical' ? 'badge-error' :
                          rule.severity === 'high' ? 'badge-warning' :
                          'badge-warning'
                        }`}
                      >
                        <span className="badge-dot" />
                        {rule.severity}
                      </span>
                    </td>
                    <td>
                      <span
                        className={`badge capitalize ${rule.status === 'active' ? 'badge-success' : 'badge-info'}`}
                      >
                        <span className="badge-dot" />
                        {rule.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          className="p-1 text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded"
                          onClick={() => setEditing(rule)}
                          title={t('common.edit')}
                        >
                          <Edit2 size={16} />
                        </button>
                        <button
                          className="p-1 text-slate-600 hover:text-red-600 hover:bg-red-50 rounded"
                          onClick={() => setDeleteTarget(rule)}
                          title={t('common.delete')}
                        >
                          <Trash2 size={16} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {(isCreating || editing) && (
        <RuleFormModal initial={editing} saving={saving} onCancel={closeForm} onSave={handleSave} />
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

function RuleFormModal({
  initial,
  saving,
  onCancel,
  onSave,
}: {
  initial: DataQualityRule | null;
  saving: boolean;
  onCancel: () => void;
  onSave: (form: {
    name: string;
    dimension: DataQualityDimension;
    rule_type: string;
    severity: RuleSeverity;
    data_source?: string;
    target_field?: string;
  }) => void;
}) {
  const { t } = useTranslation();
  const [name, setName] = useState(initial?.name ?? '');
  const [dimension, setDimension] = useState<DataQualityDimension>(
    initial?.dimension ?? DataQualityDimension.COMPLETENESS
  );
  const [ruleType, setRuleType] = useState(initial?.rule_type ?? 'required_field');
  const [severity, setSeverity] = useState<RuleSeverity>(initial?.severity ?? RuleSeverity.MEDIUM);
  const [dataSource, setDataSource] = useState(initial?.data_source ?? '');
  const [targetField, setTargetField] = useState(initial?.target_field ?? '');

  return (
    <div className="fixed inset-0 bg-slate-950/60 backdrop-blur-sm flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-2xl max-w-md w-full mx-4">
        <div className="p-6 border-b border-slate-200">
          <h2 className="text-lg font-semibold text-slate-900">
            {initial ? t('common.edit') : t('common.add')} {t('dataQuality.title')}
          </h2>
        </div>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            onSave({
              name,
              dimension,
              rule_type: ruleType,
              severity,
              data_source: dataSource || undefined,
              target_field: targetField || undefined,
            });
          }}
        >
          <div className="p-6 space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">{t('common.name')}</label>
              <input className="input-base" value={name} onChange={(e) => setName(e.target.value)} required autoFocus />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">{t('dataQuality.dimensions')}</label>
                <select
                  className="input-base"
                  value={dimension}
                  onChange={(e) => setDimension(e.target.value as DataQualityDimension)}
                >
                  {DIMENSIONS.map((d) => (
                    <option key={d} value={d}>{d}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">{t('dataQuality.severity')}</label>
                <select
                  className="input-base"
                  value={severity}
                  onChange={(e) => setSeverity(e.target.value as RuleSeverity)}
                >
                  {SEVERITIES.map((s) => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">{t('dataQuality.ruleType')}</label>
              <input className="input-base" value={ruleType} onChange={(e) => setRuleType(e.target.value)} required />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">{t('dataQuality.dataSource')}</label>
                <input className="input-base" value={dataSource} onChange={(e) => setDataSource(e.target.value)} />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">{t('dataQuality.targetField')}</label>
                <input className="input-base" value={targetField} onChange={(e) => setTargetField(e.target.value)} />
              </div>
            </div>
          </div>
          <div className="p-6 border-t border-slate-200 flex justify-end gap-3">
            <button
              type="button"
              onClick={onCancel}
              className="px-4 py-2 text-slate-700 border border-slate-300 rounded-lg hover:bg-slate-50 transition-colors font-medium"
            >
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
