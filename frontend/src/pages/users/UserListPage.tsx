import { useTranslation } from 'react-i18next';
import { Plus, Trash2, Edit2 } from 'lucide-react';

export function UserListPage() {
  const { t } = useTranslation();

  // Placeholder data
  const users = [
    { id: 1, email: 'admin@example.com', full_name: 'Administrator', role: 'Super Admin' },
    { id: 2, email: 'user@example.com', full_name: 'John Doe', role: 'User' },
  ];

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-3xl font-bold text-slate-900">{t('nav.users')}</h1>
        <button className="flex items-center gap-2 btn-primary">
          <Plus size={18} />
          {t('common.add')}
        </button>
      </div>

      <div className="card-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="border-b border-slate-200 bg-slate-50">
              <tr>
                <th className="text-left px-6 py-3 text-sm font-semibold text-slate-900">{t('auth.email')}</th>
                <th className="text-left px-6 py-3 text-sm font-semibold text-slate-900">{t('auth.fullName')}</th>
                <th className="text-left px-6 py-3 text-sm font-semibold text-slate-900">{t('auth.role')}</th>
                <th className="text-right px-6 py-3 text-sm font-semibold text-slate-900">{t('common.actions')}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {users.map((user) => (
                <tr key={user.id} className="hover:bg-slate-50">
                  <td className="px-6 py-4 text-sm text-slate-900">{user.email}</td>
                  <td className="px-6 py-4 text-sm text-slate-900">{user.full_name}</td>
                  <td className="px-6 py-4 text-sm text-slate-600">{user.role}</td>
                  <td className="px-6 py-4 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <button className="p-1 text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded">
                        <Edit2 size={16} />
                      </button>
                      <button className="p-1 text-slate-600 hover:text-red-600 hover:bg-red-50 rounded">
                        <Trash2 size={16} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
