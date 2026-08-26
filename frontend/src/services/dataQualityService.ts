import axios from 'axios';
import {
  DataQualityRule,
  CreateDataQualityRuleRequest,
  UpdateDataQualityRuleRequest,
  DataQualityRuleListResponse,
  DataQualityMetrics,
} from '../types/dataQuality';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:80/api';

const api = axios.create({
  baseURL: `${API_BASE_URL}/v1/data-quality`,
  withCredentials: true,
});

export const dataQualityService = {
  // Rules CRUD
  createRule: async (data: CreateDataQualityRuleRequest): Promise<DataQualityRule> => {
    const response = await api.post('/rules', data);
    return response.data;
  },

  listRules: async (
    dimension?: string,
    status?: string,
    page: number = 1,
    pageSize: number = 10
  ): Promise<DataQualityRuleListResponse> => {
    const params = new URLSearchParams();
    if (dimension) params.append('dimension', dimension);
    if (status) params.append('status', status);
    params.append('page', page.toString());
    params.append('page_size', pageSize.toString());

    const response = await api.get('/rules', { params });
    return response.data;
  },

  getRule: async (ruleId: string): Promise<DataQualityRule> => {
    const response = await api.get(`/rules/${ruleId}`);
    return response.data;
  },

  updateRule: async (ruleId: string, data: UpdateDataQualityRuleRequest): Promise<DataQualityRule> => {
    const response = await api.put(`/rules/${ruleId}`, data);
    return response.data;
  },

  deleteRule: async (ruleId: string): Promise<void> => {
    await api.delete(`/rules/${ruleId}`);
  },

  // Results
  getRuleResults: async (
    ruleId: string,
    page: number = 1,
    pageSize: number = 10
  ): Promise<DataQualityRuleListResponse> => {
    const params = new URLSearchParams();
    params.append('page', page.toString());
    params.append('page_size', pageSize.toString());

    const response = await api.get(`/rules/${ruleId}/results`, { params });
    return response.data;
  },

  // Metrics
  getMetrics: async (): Promise<DataQualityMetrics> => {
    const response = await api.get('/metrics');
    return response.data;
  },
};
