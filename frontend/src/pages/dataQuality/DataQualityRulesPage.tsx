import { useTranslation } from 'react-i18next';
import { Plus, Trash2, Edit2 } from 'lucide-react';

export default function DataQualityRulesPage() {
  const { t } = useTranslation();

  const rules = [
    { id: 1, name: 'Not Null Check', dataset: 'Customers', type: 'Validity', status: 'Active' },
    { id: 2, name: 'Format Check', dataset: 'Orders', type: 'Validity', status: 'Active' },
  ];

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-3xl font-bold text-slate-900">{t('dataQuality.rules')}</h1>
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
                <th className="text-left px-6 py-3 text-sm font-semibold text-slate-900">{t('common.dataset')}</th>
                <th className="text-left px-6 py-3 text-sm font-semibold text-slate-900">{t('common.type')}</th>
                <th className="text-left px-6 py-3 text-sm font-semibold text-slate-900">{t('common.status')}</th>
                <th className="text-right px-6 py-3 text-sm font-semibold text-slate-900">{t('common.actions')}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {rules.map((rule) => (
                <tr key={rule.id} className="hover:bg-slate-50">
                  <td className="px-6 py-4 text-sm font-medium text-slate-900">{rule.name}</td>
                  <td className="px-6 py-4 text-sm text-slate-600">{rule.dataset}</td>
                  <td className="px-6 py-4 text-sm text-slate-600">{rule.type}</td>
                  <td className="px-6 py-4 text-sm">
                    <span className="px-2 py-1 bg-green-100 text-green-800 rounded-full text-xs font-medium">
                      {rule.status}
                    </span>
                  </td>
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
