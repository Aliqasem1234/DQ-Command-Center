import { api } from './api';
import type { DataDomain, Dataset } from '../types';

export const domainService = {
  async list(page = 1, pageSize = 50): Promise<DataDomain[]> {
    const response = await api.get<DataDomain[]>('/v1/domains', { params: { page, page_size: pageSize } });
    return response.data;
  },

  async create(data: { name: string; description?: string }): Promise<DataDomain> {
    const response = await api.post<DataDomain>('/v1/domains', data);
    return response.data;
  },

  async listDatasetsInDomain(domainId: string): Promise<Dataset[]> {
    const response = await api.get<Dataset[]>(`/v1/domains/${domainId}/datasets`);
    return response.data;
  },

  async listAllDatasets(): Promise<Dataset[]> {
    const response = await api.get<Dataset[]>('/v1/datasets');
    return response.data;
  },

  async getDataset(datasetId: string): Promise<Dataset> {
    const response = await api.get<Dataset>(`/v1/datasets/${datasetId}`);
    return response.data;
  },
};
