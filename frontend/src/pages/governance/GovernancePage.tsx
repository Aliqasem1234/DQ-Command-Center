import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Plus, Trash2, Shield, FileText } from 'lucide-react';
import { governanceService } from '../../services/governanceService';
import { domainService } from '../../services/domainService';
import { getErrorMessage } from '../../services/api';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { EmptyState } from '../../components/common/EmptyState';
import { ConfirmDialog } from '../../components/common/ConfirmDialog';
import type { GovernanceAssignment, GovernancePolicy, GovernanceRole, GovernancePolicyStatus } from '../../types';
import { usePermission } from '../../hooks/usePermission';
import { PERMISSIONS } from '../../auth/permissions';

type Section = 'assignments' | 'policies';

const ROLE_KEY: Record<GovernanceRole, string> = {
  owner: 'governance.roleOwner',
  steward: 'governance.roleSteward',
  curator: 'governance.roleCurator',
  analyst: 'governance.roleAnalyst',
};

const POLICY_TYPE_KEY: Record<string, string> = {
  retention: 'governance.policyRetention',
  access: 'governance.policyAccess',
  quality: 'governance.policyQuality',
  privacy: 'governance.policyPrivacy',
};

const POLICY_STATUS_BADGE: Record<GovernancePolicyStatus, string> = {
  draft: 'badge-info',
  approved: 'badge-info',
  active: 'badge-success',
  deprecated: 'badge-warning',
  retired: 'badge-error',
};

export function GovernancePage() {
  const { t } = useTranslation();
  const [section, setSection] = useState<Section>('assignments');

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">{t('governance.title')}</h1>
          <p className="text-slate-600 text-sm mt-1">{t('governance.subtitle')}</p>
        </div>
      </div>

      <div className="flex gap-1 border-b border-slate-200 mb-6">
        <button
          onClick={() => setSection('assignments')}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors flex items-center gap-2 ${
            section === 'assignments' ? 'border-primary-600 text-primary-700' : 'border-transparent text-slate-600 hover:text-slate-900'
          }`}
        >
          <Shield size={16} /> {t('governance.assignments')}
        </button>
        <button
          onClick={() => setSection('policies')}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors flex items-center gap-2 ${
            section === 'policies' ? 'border-primary-600 text-primary-700' : 'border-transparent text-slate-600 hover:text-slate-900'
          }`}
        >
          <FileText size={16} /> {t('governance.policies')}
        </button>
      </div>

      {section === 'assignments' ? <AssignmentsSection /> : <PoliciesSection />}
    </div>
  );
}

function AssignmentsSection() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const canManage = usePermission(PERMISSIONS.governanceManage);
  const { data, isLoading, error } = useQuery({
    queryKey: ['governance-assignments'],
    queryFn: () => governanceService.listAssignments(1, 100),
  });
  const [isCreating, setIsCreating] = useState(false);
  const [revokeTarget, setRevokeTarget] = useState<GovernanceAssignment | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  const assignments = data?.items ?? [];

  const handleRevoke = async () => {
    if (!revokeTarget) return;
    try {
      await governanceService.revokeAssignment(revokeTarget.id);
      await queryClient.invalidateQueries({ queryKey: ['governance-assignments'] });
    } catch (err) {
      setFormError(getErrorMessage(err));
    } finally {
      setRevokeTarget(null);
    }
  };

  return (
    <div>
      {canManage && (
        <div className="flex justify-end mb-4">
          <button className="btn-primary flex items-center gap-2" onClick={() => setIsCreating(true)}>
            <Plus size={18} /> {t('governance.assignRole')}
          </button>
        </div>
      )}

      {formError && <div className="alert alert-error mb-4">{formError}</div>}

      <div className="card-lg overflow-hidden">
        {isLoading ? (
          <LoadingSpinner />
        ) : error ? (
          <div className="p-6 text-sm text-red-700">{getErrorMessage(error)}</div>
        ) : assignments.length === 0 ? (
          <EmptyState
            icon={<Shield size={40} />}
            title={t('governance.noAssignmentsTitle')}
            message={t('governance.noAssignmentsMessage')}
            action={
              canManage ? (
                <button className="btn-primary" onClick={() => setIsCreating(true)}>
                  {t('governance.assignRole')}
                </button>
              ) : undefined
            }
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="border-b border-slate-200 bg-slate-50">
                <tr>
                  <th className="text-left px-6 py-3 text-sm font-semibold text-slate-900">{t('governance.role')}</th>
                  <th className="text-left px-6 py-3 text-sm font-semibold text-slate-900">{t('governance.scope')}</th>
                  <th className="text-left px-6 py-3 text-sm font-semibold text-slate-900">{t('governance.assignedTo')}</th>
                  <th className="text-left px-6 py-3 text-sm font-semibold text-slate-900">{t('common.status')}</th>
                  <th className="text-right px-6 py-3 text-sm font-semibold text-slate-900">{t('common.actions')}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {assignments.map((a) => (
                  <tr key={a.id} className="hover:bg-slate-50">
                    <td className="px-6 py-4 text-sm">
                      <span className="badge badge-info">{t(ROLE_KEY[a.role])}</span>
                    </td>
                    <td className="px-6 py-4 text-sm font-medium text-slate-900">
                      {a.scope_name || '—'}
                      <span className="ml-2 text-xs text-slate-500">
                        {a.domain_id ? t('datasets.domain') : a.dataset_id ? t('common.dataset') : t('datasets.columnHeader')}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm text-slate-600">{a.user_name || '—'}</td>
                    <td className="px-6 py-4 text-sm">
                      <span className={`badge ${a.is_active ? 'badge-success' : 'badge-warning'}`}>
                        {a.is_active ? t('common.active') : t('common.inactive')}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-right">
                      {canManage && (
                        <button
                          className="p-1 text-slate-600 hover:text-red-600 hover:bg-red-50 rounded"
                          onClick={() => setRevokeTarget(a)}
                          title={t('governance.revoke')}
                        >
                          <Trash2 size={16} />
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {isCreating && (
        <AssignmentFormModal
          onCancel={() => setIsCreating(false)}
          onCreated={async () => {
            setIsCreating(false);
            await queryClient.invalidateQueries({ queryKey: ['governance-assignments'] });
          }}
        />
      )}

      <ConfirmDialog
        open={!!revokeTarget}
        title={t('governance.revoke')}
        message={t('governance.revokeConfirm')}
        onConfirm={handleRevoke}
        onCancel={() => setRevokeTarget(null)}
      />
    </div>
  );
}

function AssignmentFormModal({ onCancel, onCreated }: { onCancel: () => void; onCreated: () => void }) {
  const { t } = useTranslation();
  const [scopeType, setScopeType] = useState<'domain' | 'dataset'>('domain');
  const [scopeId, setScopeId] = useState('');
  const [role, setRole] = useState<GovernanceRole>('owner');
  const [email, setEmail] = useState('');
  const [responsibility, setResponsibility] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { data: domains } = useQuery({ queryKey: ['domains'], queryFn: () => domainService.list(1, 50) });
  const { data: datasets } = useQuery({ queryKey: ['all-datasets'], queryFn: () => domainService.listAllDatasets() });

  const scopeOptions = scopeType === 'domain' ? (domains ?? []) : (datasets ?? []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!scopeId || !email.trim()) return;
    setSaving(true);
    setError(null);
    try {
      // Sharing is by exact email address: you can only add someone whose
      // address you already know (the API never lists registered users).
      const target = await governanceService.findUserByEmail(email.trim());
      if (!target) {
        setError(t('governance.userNotFound'));
        return;
      }
      await governanceService.createAssignment({
        role,
        user_id: target.id,
        domain_id: scopeType === 'domain' ? scopeId : null,
        dataset_id: scopeType === 'dataset' ? scopeId : null,
        responsibility_description: responsibility || undefined,
      });
      onCreated();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-slate-950/60 backdrop-blur-xs flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-2xl max-w-md w-full mx-4">
        <div className="p-6 border-b border-slate-200">
          <h2 className="text-lg font-semibold text-slate-900">{t('governance.assignRole')}</h2>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="p-6 space-y-4">
            {error && <div className="alert alert-error text-sm">{error}</div>}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">{t('governance.role')}</label>
              <select className="input-base" value={role} onChange={(e) => setRole(e.target.value as GovernanceRole)}>
                {(Object.keys(ROLE_KEY) as GovernanceRole[]).map((r) => (
                  <option key={r} value={r}>{t(ROLE_KEY[r])}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">{t('governance.scope')}</label>
              <div className="flex gap-2 mb-2">
                <select className="input-base w-auto" value={scopeType} onChange={(e) => { setScopeType(e.target.value as 'domain' | 'dataset'); setScopeId(''); }}>
                  <option value="domain">{t('datasets.domain')}</option>
                  <option value="dataset">{t('common.dataset')}</option>
                </select>
                <select className="input-base" value={scopeId} onChange={(e) => setScopeId(e.target.value)} required>
                  <option value="" disabled>{t('governance.selectScope')}</option>
                  {scopeOptions.map((o) => (
                    <option key={o.id} value={o.id}>{o.name}</option>
                  ))}
                </select>
              </div>
            </div>
            <div>
              <label htmlFor="assign-email" className="block text-sm font-medium text-slate-700 mb-1">{t('governance.assignedTo')}</label>
              <input
                id="assign-email"
                type="email"
                className="input-base"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder={t('governance.assigneeEmailPlaceholder')}
                autoComplete="off"
                required
              />
              <p className="text-xs text-slate-500 mt-1">{t('governance.assigneeEmailHelp')}</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">{t('governance.responsibility')}</label>
              <textarea className="input-base" value={responsibility} onChange={(e) => setResponsibility(e.target.value)} rows={2} />
            </div>
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

function PoliciesSection() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const canManage = usePermission(PERMISSIONS.governanceManage);
  const { data, isLoading, error } = useQuery({
    queryKey: ['governance-policies'],
    queryFn: () => governanceService.listPolicies(1, 100),
  });
  const [isCreating, setIsCreating] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<GovernancePolicy | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  const policies = data?.items ?? [];

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await governanceService.deletePolicy(deleteTarget.id);
      await queryClient.invalidateQueries({ queryKey: ['governance-policies'] });
    } catch (err) {
      setFormError(getErrorMessage(err));
    } finally {
      setDeleteTarget(null);
    }
  };

  return (
    <div>
      {canManage && (
        <div className="flex justify-end mb-4">
          <button className="btn-primary flex items-center gap-2" onClick={() => setIsCreating(true)}>
            <Plus size={18} /> {t('governance.newPolicy')}
          </button>
        </div>
      )}

      {formError && <div className="alert alert-error mb-4">{formError}</div>}

      <div className="card-lg overflow-hidden">
        {isLoading ? (
          <LoadingSpinner />
        ) : error ? (
          <div className="p-6 text-sm text-red-700">{getErrorMessage(error)}</div>
        ) : policies.length === 0 ? (
          <EmptyState
            icon={<FileText size={40} />}
            title={t('governance.noPoliciesTitle')}
            message={t('governance.noPoliciesMessage')}
            action={
              canManage ? (
                <button className="btn-primary" onClick={() => setIsCreating(true)}>
                  {t('governance.newPolicy')}
                </button>
              ) : undefined
            }
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="border-b border-slate-200 bg-slate-50">
                <tr>
                  <th className="text-left px-6 py-3 text-sm font-semibold text-slate-900">{t('common.name')}</th>
                  <th className="text-left px-6 py-3 text-sm font-semibold text-slate-900">{t('governance.policyType')}</th>
                  <th className="text-left px-6 py-3 text-sm font-semibold text-slate-900">{t('common.status')}</th>
                  <th className="text-right px-6 py-3 text-sm font-semibold text-slate-900">{t('common.actions')}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {policies.map((p) => (
                  <tr key={p.id} className="hover:bg-slate-50">
                    <td className="px-6 py-4 text-sm font-medium text-slate-900">{p.name}</td>
                    <td className="px-6 py-4 text-sm text-slate-600">
                      {POLICY_TYPE_KEY[p.policy_type] ? t(POLICY_TYPE_KEY[p.policy_type]) : p.policy_type}
                    </td>
                    <td className="px-6 py-4 text-sm">
                      <span className={`badge ${POLICY_STATUS_BADGE[p.status]} capitalize`}>{p.status}</span>
                    </td>
                    <td className="px-6 py-4 text-right">
                      {canManage && (
                        <button
                          className="p-1 text-slate-600 hover:text-red-600 hover:bg-red-50 rounded"
                          onClick={() => setDeleteTarget(p)}
                          title={t('common.delete')}
                        >
                          <Trash2 size={16} />
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {isCreating && (
        <PolicyFormModal
          onCancel={() => setIsCreating(false)}
          onCreated={async () => {
            setIsCreating(false);
            await queryClient.invalidateQueries({ queryKey: ['governance-policies'] });
          }}
        />
      )}

      <ConfirmDialog
        open={!!deleteTarget}
        title={t('common.delete')}
        message={t('governance.deletePolicyConfirm')}
        onConfirm={handleDelete}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  );
}

function PolicyFormModal({ onCancel, onCreated }: { onCancel: () => void; onCreated: () => void }) {
  const { t } = useTranslation();
  const [scopeType, setScopeType] = useState<'domain' | 'dataset'>('domain');
  const [scopeId, setScopeId] = useState('');
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [policyType, setPolicyType] = useState('retention');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { data: domains } = useQuery({ queryKey: ['domains'], queryFn: () => domainService.list(1, 50) });
  const { data: datasets } = useQuery({ queryKey: ['all-datasets'], queryFn: () => domainService.listAllDatasets() });
  const scopeOptions = scopeType === 'domain' ? (domains ?? []) : (datasets ?? []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!scopeId || !name) return;
    setSaving(true);
    setError(null);
    try {
      await governanceService.createPolicy({
        name,
        description: description || undefined,
        policy_type: policyType,
        domain_id: scopeType === 'domain' ? scopeId : null,
        dataset_id: scopeType === 'dataset' ? scopeId : null,
      });
      onCreated();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-slate-950/60 backdrop-blur-xs flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-2xl max-w-md w-full mx-4">
        <div className="p-6 border-b border-slate-200">
          <h2 className="text-lg font-semibold text-slate-900">{t('governance.newPolicy')}</h2>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="p-6 space-y-4">
            {error && <div className="alert alert-error text-sm">{error}</div>}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">{t('governance.policyName')}</label>
              <input className="input-base" value={name} onChange={(e) => setName(e.target.value)} required autoFocus />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">{t('governance.policyDescription')}</label>
              <textarea className="input-base" value={description} onChange={(e) => setDescription(e.target.value)} rows={2} />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">{t('governance.policyType')}</label>
              <select className="input-base" value={policyType} onChange={(e) => setPolicyType(e.target.value)}>
                {Object.entries(POLICY_TYPE_KEY).map(([value, key]) => (
                  <option key={value} value={value}>{t(key)}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">{t('governance.scope')}</label>
              <div className="flex gap-2">
                <select className="input-base w-auto" value={scopeType} onChange={(e) => { setScopeType(e.target.value as 'domain' | 'dataset'); setScopeId(''); }}>
                  <option value="domain">{t('datasets.domain')}</option>
                  <option value="dataset">{t('common.dataset')}</option>
                </select>
                <select className="input-base" value={scopeId} onChange={(e) => setScopeId(e.target.value)} required>
                  <option value="" disabled>{t('governance.selectScope')}</option>
                  {scopeOptions.map((o) => (
                    <option key={o.id} value={o.id}>{o.name}</option>
                  ))}
                </select>
              </div>
            </div>
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
