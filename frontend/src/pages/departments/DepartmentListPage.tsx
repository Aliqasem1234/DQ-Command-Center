import { useTranslation } from 'react-i18next';
import { Plus, Trash2, Edit2 } from 'lucide-react';

export function DepartmentListPage() {
  const { t } = useTranslation();

  const departments = [
    { id: 1, name: 'Finance', description: 'Financial data management' },
    { id: 2, name: 'Sales', description: 'Sales and customer data' },
    { id: 3, name: 'Operations', description: 'Operational data' },
  ];

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-3xl font-bold text-slate-900">{t('nav.departments')}</h1>
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
                <th className="text-left px-6 py-3 text-sm font-semibold text-slate-900">{t('common.name')}</th>
                <th className="text-left px-6 py-3 text-sm font-semibold text-slate-900">{t('common.description')}</th>
                <th className="text-right px-6 py-3 text-sm font-semibold text-slate-900">{t('common.actions')}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {departments.map((dept) => (
                <tr key={dept.id} className="hover:bg-slate-50">
                  <td className="px-6 py-4 text-sm font-medium text-slate-900">{dept.name}</td>
                  <td className="px-6 py-4 text-sm text-slate-600">{dept.description}</td>
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
