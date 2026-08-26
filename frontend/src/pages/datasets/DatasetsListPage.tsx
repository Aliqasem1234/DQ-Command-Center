import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Upload, Database, ChevronRight } from 'lucide-react';
import { domainService } from '../../services/domainService';
import { datasetFileService } from '../../services/datasetFileService';
import { getErrorMessage } from '../../services/api';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { EmptyState } from '../../components/common/EmptyState';

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

  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const handleUpload = async (form: { domainId: string; name: string; description: string; file: File }) => {
    setSaving(true);
    setUploadError(null);
    try {
      const version = await datasetFileService.uploadNewDataset({
        domainId: form.domainId,
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
          <h1 className="text-3xl font-bold text-slate-900">Datasets</h1>
          <p className="text-slate-600 text-sm mt-1">Upload real data, profile it, and track its quality over time.</p>
        </div>
        <button className="flex items-center gap-2 btn-primary" onClick={() => setIsUploading(true)}>
          <Upload size={18} />
          Upload Dataset
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
            title="No datasets yet"
            message="Upload a CSV or Excel file to start profiling and monitoring its quality."
            action={
              <button className="btn-primary" onClick={() => setIsUploading(true)}>
                Upload your first dataset
              </button>
            }
          />
        ) : (
          <div className="divide-y divide-slate-200">
            {datasets.map((ds) => (
              <button
                key={ds.id}
                onClick={() => navigate(`/datasets/${ds.id}`)}
                className="w-full flex items-center justify-between px-6 py-4 hover:bg-slate-50 text-left transition-colors"
              >
                <div>
                  <p className="font-medium text-slate-900">{ds.name}</p>
                  <p className="text-sm text-slate-600">{ds.description || 'No description'}</p>
                </div>
                <div className="flex items-center gap-6 text-sm text-slate-500">
                  <span>{ds.row_count ?? '—'} rows</span>
                  <span className="capitalize">{ds.status}</span>
                  <ChevronRight size={18} />
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
  onUpload: (form: { domainId: string; name: string; description: string; file: File }) => void;
}) {
  const [domainId, setDomainId] = useState(domains[0]?.id || '');
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [file, setFile] = useState<File | null>(null);

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-lg max-w-lg w-full mx-4">
        <div className="p-6 border-b border-slate-200">
          <h2 className="text-lg font-semibold text-slate-900">Upload Dataset</h2>
          <p className="text-sm text-slate-600 mt-1">CSV or Excel (.xlsx), up to 50MB.</p>
        </div>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (!file || !domainId) return;
            onUpload({ domainId, name, description, file });
          }}
        >
          <div className="p-6 space-y-4">
            {error && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-800">{error}</div>
            )}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Domain</label>
              {domains.length === 0 ? (
                <p className="text-sm text-slate-500">
                  No domains exist yet. Create one from the Data Explorer first.
                </p>
              ) : (
                <select className="input-base" value={domainId} onChange={(e) => setDomainId(e.target.value)} required>
                  {domains.map((d) => (
                    <option key={d.id} value={d.id}>{d.name}</option>
                  ))}
                </select>
              )}
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Dataset name</label>
              <input className="input-base" value={name} onChange={(e) => setName(e.target.value)} required autoFocus />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Description</label>
              <textarea className="input-base" value={description} onChange={(e) => setDescription(e.target.value)} rows={2} />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">File</label>
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
              Cancel
            </button>
            <button type="submit" disabled={saving || domains.length === 0} className="btn-primary">
              {saving ? 'Uploading…' : 'Upload & Profile'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
