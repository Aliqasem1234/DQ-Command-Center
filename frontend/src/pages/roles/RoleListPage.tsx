import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Plus, Trash2, Edit2 } from 'lucide-react';
import { roleService } from '../../services/roleService';
import { getErrorMessage } from '../../services/api';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { EmptyState } from '../../components/common/EmptyState';
import { ConfirmDialog } from '../../components/common/ConfirmDialog';
import type { Role } from '../../types';

export function RoleListPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const { data, isLoading, error } = useQuery({
    queryKey: ['roles'],
    queryFn: () => roleService.list(1, 100),
  });

  const [editing, setEditing] = useState<Role | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<Role | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const closeForm = () => {
    setIsCreating(false);
    setEditing(null);
    setFormError(null);
  };

  const handleSave = async (name: string, description: string) => {
    setSaving(true);
    setFormError(null);
    try {
      if (editing) {
        await roleService.update(editing.id, { name, description });
      } else {
        await roleService.create({ name, description });
      }
      await queryClient.invalidateQueries({ queryKey: ['roles'] });
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
      await roleService.delete(deleteTarget.id);
      await queryClient.invalidateQueries({ queryKey: ['roles'] });
    } catch (err) {
      setFormError(getErrorMessage(err));
    } finally {
      setDeleteTarget(null);
    }
  };

  const roles = data?.items ?? [];

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">{t('nav.roles')}</h1>
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
        ) : roles.length === 0 ? (
          <EmptyState title={t('common.noData')} />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="border-b border-slate-200 bg-slate-50">
                <tr>
                  <th className="text-left px-6 py-3 text-sm font-semibold text-slate-900">{t('common.name')}</th>
                  <th className="text-left px-6 py-3 text-sm font-semibold text-slate-900">{t('common.description')}</th>
                  <th className="text-left px-6 py-3 text-sm font-semibold text-slate-900">{t('common.permissions')}</th>
                  <th className="text-right px-6 py-3 text-sm font-semibold text-slate-900">{t('common.actions')}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {roles.map((role) => (
                  <tr key={role.id} className="hover:bg-slate-50">
                    <td className="px-6 py-4 text-sm font-medium text-slate-900">
                      {role.name}
                      {role.is_system && (
                        <span className="ml-2 text-xs text-slate-500 bg-slate-100 px-2 py-0.5 rounded">
                          {t('common.system')}
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-sm text-slate-600">{role.description || '—'}</td>
                    <td className="px-6 py-4 text-sm text-slate-600">{role.permissions?.length ?? 0}</td>
                    <td className="px-6 py-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          className="p-1 text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded disabled:opacity-30 disabled:cursor-not-allowed"
                          onClick={() => setEditing(role)}
                          disabled={role.is_system}
                          title={role.is_system ? undefined : t('common.edit')}
                        >
                          <Edit2 size={16} />
                        </button>
                        <button
                          className="p-1 text-slate-600 hover:text-red-600 hover:bg-red-50 rounded disabled:opacity-30 disabled:cursor-not-allowed"
                          onClick={() => setDeleteTarget(role)}
                          disabled={role.is_system}
                          title={role.is_system ? undefined : t('common.delete')}
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
        <RoleFormModal initial={editing} saving={saving} onCancel={closeForm} onSave={handleSave} />
      )}

      <ConfirmDialog
        open={!!deleteTarget}
        title={t('common.delete')}
        message={t('roles.deleteConfirm')}
        onConfirm={handleDelete}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  );
}

function RoleFormModal({
  initial,
  saving,
  onCancel,
  onSave,
}: {
  initial: Role | null;
  saving: boolean;
  onCancel: () => void;
  onSave: (name: string, description: string) => void;
}) {
  const { t } = useTranslation();
  const [name, setName] = useState(initial?.name ?? '');
  const [description, setDescription] = useState(initial?.description ?? '');

  return (
    <div className="fixed inset-0 bg-slate-950/60 backdrop-blur-xs flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-2xl max-w-md w-full mx-4">
        <div className="p-6 border-b border-slate-200">
          <h2 className="text-lg font-semibold text-slate-900">
            {initial ? t('common.edit') : t('common.add')} {t('auth.role')}
          </h2>
        </div>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            onSave(name, description);
          }}
        >
          <div className="p-6 space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">{t('common.name')}</label>
              <input
                className="input-base"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                autoFocus
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">{t('common.description')}</label>
              <textarea
                className="input-base"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={3}
              />
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
