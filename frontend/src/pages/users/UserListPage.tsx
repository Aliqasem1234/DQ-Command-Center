import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Plus, UserX } from 'lucide-react';
import { userService } from '../../services/userService';
import { getErrorMessage } from '../../services/api';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { EmptyState } from '../../components/common/EmptyState';
import { ConfirmDialog } from '../../components/common/ConfirmDialog';
import type { User } from '../../types';

export function UserListPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const { data, isLoading, error } = useQuery({
    queryKey: ['users'],
    queryFn: () => userService.list(1, 100),
  });

  const [isCreating, setIsCreating] = useState(false);
  const [deactivateTarget, setDeactivateTarget] = useState<User | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const handleCreate = async (form: {
    email: string;
    username: string;
    password: string;
    full_name: string;
  }) => {
    setSaving(true);
    setFormError(null);
    try {
      await userService.create(form);
      await queryClient.invalidateQueries({ queryKey: ['users'] });
      setIsCreating(false);
    } catch (err) {
      setFormError(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  const handleDeactivate = async () => {
    if (!deactivateTarget) return;
    try {
      await userService.deactivate(deactivateTarget.id);
      await queryClient.invalidateQueries({ queryKey: ['users'] });
    } catch (err) {
      setFormError(getErrorMessage(err));
    } finally {
      setDeactivateTarget(null);
    }
  };

  const users = data?.items ?? [];

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">{t('nav.users')}</h1>
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
        ) : users.length === 0 ? (
          <EmptyState title={t('common.noData')} />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr>
                  <th>{t('auth.fullName')}</th>
                  <th>{t('auth.email')}</th>
                  <th>{t('common.departments')}</th>
                  <th>{t('common.status')}</th>
                  <th className="text-right">{t('common.actions')}</th>
                </tr>
              </thead>
              <tbody>
                {users.map((user) => (
                  <tr key={user.id}>
                    <td>
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-primary-100 dark:bg-primary-500/20 text-primary-700 dark:text-primary-400 flex items-center justify-center text-xs font-bold flex-shrink-0">
                          {user.full_name?.charAt(0).toUpperCase() || '?'}
                        </div>
                        <span className="font-medium text-slate-900">{user.full_name}</span>
                      </div>
                    </td>
                    <td className="text-slate-500">{user.email}</td>
                    <td className="text-slate-500">{user.department_name || '—'}</td>
                    <td>
                      <span className={`badge ${user.is_active ? 'badge-success' : 'badge-info'}`}>
                        <span className="badge-dot" />
                        {user.is_active ? t('common.active') : t('common.inactive')}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <button
                        className="p-1 text-slate-600 hover:text-red-600 hover:bg-red-50 rounded disabled:opacity-30 disabled:cursor-not-allowed"
                        onClick={() => setDeactivateTarget(user)}
                        disabled={!user.is_active || user.is_super_admin}
                        title={t('users.deactivateConfirm')}
                      >
                        <UserX size={16} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {isCreating && (
        <UserFormModal
          saving={saving}
          onCancel={() => {
            setIsCreating(false);
            setFormError(null);
          }}
          onSave={handleCreate}
        />
      )}

      <ConfirmDialog
        open={!!deactivateTarget}
        title={t('common.confirm')}
        message={t('users.deactivateConfirm')}
        onConfirm={handleDeactivate}
        onCancel={() => setDeactivateTarget(null)}
      />
    </div>
  );
}

function UserFormModal({
  saving,
  onCancel,
  onSave,
}: {
  saving: boolean;
  onCancel: () => void;
  onSave: (form: { email: string; username: string; password: string; full_name: string }) => void;
}) {
  const { t } = useTranslation();
  const [email, setEmail] = useState('');
  const [username, setUsername] = useState('');
  const [fullName, setFullName] = useState('');
  const [password, setPassword] = useState('');

  return (
    <div className="fixed inset-0 bg-slate-950/60 backdrop-blur-sm flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-2xl max-w-md w-full mx-4">
        <div className="p-6 border-b border-slate-200">
          <h2 className="text-lg font-semibold text-slate-900">
            {t('common.add')} {t('auth.user')}
          </h2>
        </div>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            onSave({ email, username, password, full_name: fullName });
          }}
        >
          <div className="p-6 space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">{t('auth.email')}</label>
              <input
                type="email"
                className="input-base"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoFocus
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">{t('auth.username')}</label>
              <input
                className="input-base"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">{t('auth.fullName')}</label>
              <input
                className="input-base"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">{t('auth.password')}</label>
              <input
                type="password"
                className="input-base"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={8}
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
