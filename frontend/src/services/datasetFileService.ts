import { api } from './api';
import type {
  DatasetVersion, ProfileSummary, ScanResult, CleaningOperation,
  CleaningPreview, QualityComparison, RowPreview,
} from '../types';

export const datasetFileService = {
  async uploadNewDataset(params: {
    domainId: string;
    name: string;
    description?: string;
    file: File;
  }): Promise<DatasetVersion> {
    const form = new FormData();
    form.append('domain_id', params.domainId);
    form.append('name', params.name);
    if (params.description) form.append('description', params.description);
    form.append('file', params.file);
    const response = await api.post<DatasetVersion>('/v1/dataset-files/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  async uploadNewVersion(datasetId: string, file: File): Promise<DatasetVersion> {
    const form = new FormData();
    form.append('file', file);
    const response = await api.post<DatasetVersion>(
      `/v1/dataset-files/${datasetId}/versions/upload`,
      form,
      { headers: { 'Content-Type': 'multipart/form-data' } }
    );
    return response.data;
  },

  async listVersions(datasetId: string): Promise<DatasetVersion[]> {
    const response = await api.get<DatasetVersion[]>(`/v1/dataset-files/${datasetId}/versions`);
    return response.data;
  },

  async getVersion(datasetId: string, versionId: string): Promise<DatasetVersion> {
    const response = await api.get<DatasetVersion>(`/v1/dataset-files/${datasetId}/versions/${versionId}`);
    return response.data;
  },

  async previewRows(datasetId: string, versionId: string, page = 1, pageSize = 50): Promise<RowPreview> {
    const response = await api.get<RowPreview>(`/v1/dataset-files/${datasetId}/versions/${versionId}/rows`, {
      params: { page, page_size: pageSize },
    });
    return response.data;
  },

  async reprofile(datasetId: string, versionId: string): Promise<ProfileSummary> {
    const response = await api.post<ProfileSummary>(`/v1/dataset-files/${datasetId}/versions/${versionId}/profile`);
    return response.data;
  },

  async scan(datasetId: string, versionId: string): Promise<ScanResult> {
    const response = await api.post<ScanResult>(`/v1/dataset-files/${datasetId}/versions/${versionId}/scan`);
    return response.data;
  },

  async previewCleaning(datasetId: string, versionId: string, operations: CleaningOperation[]): Promise<CleaningPreview> {
    const response = await api.post<CleaningPreview>(
      `/v1/dataset-files/${datasetId}/versions/${versionId}/clean/preview`,
      { operations }
    );
    return response.data;
  },

  async applyCleaning(datasetId: string, versionId: string, operations: CleaningOperation[]): Promise<DatasetVersion> {
    const response = await api.post<DatasetVersion>(
      `/v1/dataset-files/${datasetId}/versions/${versionId}/clean`,
      { operations }
    );
    return response.data;
  },

  async downloadFile(datasetId: string, versionId: string, filename: string): Promise<void> {
    // The download endpoint requires the same Authorization header every
    // other request uses, so a plain <a href> can't hit it directly (the
    // browser won't attach a header stored in JS state to a navigation).
    // Fetch it through the authenticated client instead and hand the
    // browser a local blob URL to save.
    const response = await api.get(`/v1/dataset-files/${datasetId}/versions/${versionId}/download`, {
      responseType: 'blob',
    });
    const blobUrl = window.URL.createObjectURL(response.data as Blob);
    const link = document.createElement('a');
    link.href = blobUrl;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(blobUrl);
  },

  async qualityComparison(datasetId: string): Promise<QualityComparison> {
    const response = await api.get<QualityComparison>(`/v1/dataset-files/${datasetId}/quality-comparison`);
    return response.data;
  },
};
