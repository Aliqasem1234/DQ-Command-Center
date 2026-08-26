import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Upload, Database, ChevronRight, Plus } from 'lucide-react';
import { domainService } from '../../services/domainService';
import { datasetFileService } from '../../services/datasetFileService';
import { getErrorMessage } from '../../services/api';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { EmptyState } from '../../components/common/EmptyState';

const NEW_DOMAIN_SENTINEL = '__new__';

export function DatasetsListPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { data: datasets, isLoading, error } = useQuery({
    queryKey: ['all-datasets'],
    queryFn: () => domainService.listAllDatasets(),
  });

  const { data: domains } = useQuery({
    queryKey: ['domains'],
    queryFn: () => domainService.list(1, 50),
  });
  const domainById = new Map((domains ?? []).map((d) => [d.id, d.name]));

  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const handleUpload = async (form: { domainId: string; newDomainName: string; name: string; description: string; file: File }) => {
    setSaving(true);
    setUploadError(null);
    try {
      let domainId = form.domainId;
      if (domainId === NEW_DOMAIN_SENTINEL) {
        const newDomain = await domainService.create({ name: form.newDomainName });
        domainId = newDomain.id;
        await queryClient.invalidateQueries({ queryKey: ['domains'] });
      }
      const version = await datasetFileService.uploadNewDataset({
        domainId: domainId || undefined,
        name: form.name,
        description: form.description || undefined,
        file: form.file,
      });
      await queryClient.invalidateQueries({ queryKey: ['all-datasets'] });
      setIsUploading(false);
      navigate(`/datasets/${version.dataset_id}`);
    } catch (err) {
      setUploadError(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">{t('datasets.title')}</h1>
          <p className="text-slate-600 text-sm mt-1">{t('datasets.subtitle')}</p>
        </div>
        <button className="flex items-center gap-2 btn-primary" onClick={() => setIsUploading(true)}>
          <Upload size={18} />
          {t('datasets.uploadDataset')}
        </button>
      </div>

      <div className="card-lg overflow-hidden">
        {isLoading ? (
          <LoadingSpinner />
        ) : error ? (
          <div className="p-6 text-sm text-red-700">{getErrorMessage(error)}</div>
        ) : !datasets || datasets.length === 0 ? (
          <EmptyState
            icon={<Database size={40} />}
            title={t('datasets.noDatasetsTitle')}
            message={t('datasets.noDatasetsMessage')}
            action={
              <button className="btn-primary" onClick={() => setIsUploading(true)}>
                {t('datasets.uploadFirst')}
              </button>
            }
          />
        ) : (
          <div className="divide-y divide-slate-100 dark:divide-slate-800">
            {datasets.map((ds) => (
              <button
                key={ds.id}
                onClick={() => navigate(`/datasets/${ds.id}`)}
                className="w-full flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 px-6 py-4 hover:bg-slate-50 dark:hover:bg-slate-800/60 text-left transition-colors"
              >
                <div className="flex items-center gap-3.5 min-w-0">
                  <div className="icon-badge icon-badge-blue">
                    <Database className="w-[18px] h-[18px]" />
                  </div>
                  <div className="min-w-0">
                    <p className="font-medium text-slate-900 truncate">{ds.name}</p>
                    <p className="text-sm text-slate-500 truncate">{ds.description || t('datasets.noDescription')}</p>
                  </div>
                </div>
                <div className="flex items-center gap-4 sm:gap-6 text-sm text-slate-500 flex-shrink-0 pl-[52px] sm:pl-0">
                  <span className="whitespace-nowrap text-xs text-slate-400 border border-slate-200 dark:border-slate-700 rounded-md px-2 py-0.5">
                    {ds.domain_id ? (domainById.get(ds.domain_id) ?? t('datasets.domain')) : t('datasets.noDomainOption')}
                  </span>
                  <span className="whitespace-nowrap">{ds.row_count ?? '—'} {t('datasets.rows')}</span>
                  <span className={`badge whitespace-nowrap ${ds.status === 'active' ? 'badge-success' : 'badge-info'}`}>
                    <span className="badge-dot" />
                    {ds.status === 'active' ? t('common.active') : ds.status === 'inactive' ? t('common.inactive') : ds.status}
                  </span>
                  <ChevronRight size={18} className="hidden sm:block text-slate-300 dark:text-slate-600" />
                </div>
              </button>
            ))}
          </div>
        )}
      </div>

      {isUploading && (
        <UploadModal
          domains={domains || []}
          saving={saving}
          error={uploadError}
          onCancel={() => {
            setIsUploading(false);
            setUploadError(null);
          }}
          onUpload={handleUpload}
        />
      )}
    </div>
  );
}

function UploadModal({
  domains,
  saving,
  error,
  onCancel,
  onUpload,
}: {
  domains: { id: string; name: string }[];
  saving: boolean;
  error: string | null;
  onCancel: () => void;
  onUpload: (form: { domainId: string; newDomainName: string; name: string; description: string; file: File }) => void;
}) {
  const { t } = useTranslation();
  const [domainId, setDomainId] = useState('');
  const [newDomainName, setNewDomainName] = useState('');
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [file, setFile] = useState<File | null>(null);

  const isCreatingDomain = domainId === NEW_DOMAIN_SENTINEL;

  return (
    <div className="fixed inset-0 bg-slate-950/60 backdrop-blur-sm flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-2xl max-w-lg w-full mx-4">
        <div className="p-6 border-b border-slate-200">
          <h2 className="text-lg font-semibold text-slate-900">{t('datasets.uploadDataset')}</h2>
          <p className="text-sm text-slate-600 mt-1">{t('datasets.uploadModalSubtitle')}</p>
        </div>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (!file) return;
            if (isCreatingDomain && !newDomainName.trim()) return;
            onUpload({ domainId, newDomainName: newDomainName.trim(), name, description, file });
          }}
        >
          <div className="p-6 space-y-4">
            {error && (
              <div className="alert alert-error text-sm">{error}</div>
            )}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                {t('datasets.domain')}
                <span className="ml-1.5 font-normal text-slate-400">{t('common.optional')}</span>
              </label>
              <select className="input-base" value={domainId} onChange={(e) => setDomainId(e.target.value)}>
                <option value="">{t('datasets.noDomainOption')}</option>
                {domains.map((d) => (
                  <option key={d.id} value={d.id}>{d.name}</option>
                ))}
                <option value={NEW_DOMAIN_SENTINEL}>{t('datasets.createNewDomain')}</option>
              </select>
              <p className="text-xs text-slate-500 mt-1.5">{t('datasets.domainHint')}</p>
              {isCreatingDomain && (
                <input
                  className="input-base mt-2"
                  value={newDomainName}
                  onChange={(e) => setNewDomainName(e.target.value)}
                  placeholder={t('datasets.newDomainNamePlaceholder')}
                  required
                  autoFocus
                />
              )}
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">{t('datasets.datasetName')}</label>
              <input className="input-base" value={name} onChange={(e) => setName(e.target.value)} required autoFocus={!isCreatingDomain} />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">{t('common.description')}</label>
              <textarea className="input-base" value={description} onChange={(e) => setDescription(e.target.value)} rows={2} />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">{t('datasets.file')}</label>
              <input
                type="file"
                accept=".csv,.xlsx,.xls"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
                className="input-base"
                required
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
            <button type="submit" disabled={saving} className="btn-primary flex items-center gap-2">
              {isCreatingDomain && !saving && <Plus size={16} />}
              {saving ? t('datasets.uploading') : t('datasets.uploadAndProfile')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
