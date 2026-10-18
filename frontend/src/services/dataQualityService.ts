import { api } from './api';
import {
  DataQualityRule,
  CreateDataQualityRuleRequest,
  UpdateDataQualityRuleRequest,
  DataQualityRuleListResponse,
  DataQualityMetrics,
  RuleRunResult,
} from '../types/dataQuality';

export const dataQualityService = {
  // Rules CRUD
  createRule: async (data: CreateDataQualityRuleRequest): Promise<DataQualityRule> => {
    const response = await api.post('/v1/data-quality/rules', data);
    return response.data;
  },

  listRules: async (
    dimension?: string,
    status?: string,
    page: number = 1,
    pageSize: number = 10
  ): Promise<DataQualityRuleListResponse> => {
    const params: Record<string, string | number> = { page, page_size: pageSize };
    if (dimension) params.dimension = dimension;
    if (status) params.status = status;

    const response = await api.get('/v1/data-quality/rules', { params });
    return response.data;
  },

  getRule: async (ruleId: string): Promise<DataQualityRule> => {
    const response = await api.get(`/v1/data-quality/rules/${ruleId}`);
    return response.data;
  },

  updateRule: async (ruleId: string, data: UpdateDataQualityRuleRequest): Promise<DataQualityRule> => {
    const response = await api.put(`/v1/data-quality/rules/${ruleId}`, data);
    return response.data;
  },

  deleteRule: async (ruleId: string): Promise<void> => {
    await api.delete(`/v1/data-quality/rules/${ruleId}`);
  },

  // Results
  getRuleResults: async (
    ruleId: string,
    page: number = 1,
    pageSize: number = 10
  ): Promise<DataQualityRuleListResponse> => {
    const response = await api.get(`/v1/data-quality/rules/${ruleId}/results`, {
      params: { page, page_size: pageSize },
    });
    return response.data;
  },

  // Metrics
  /** Run an executable rule against the latest version of its dataset. */
  runRule: async (ruleId: string): Promise<RuleRunResult> => {
    const response = await api.post<RuleRunResult>(`/v1/data-quality/rules/${ruleId}/run`);
    return response.data;
  },

  getMetrics: async (): Promise<DataQualityMetrics> => {
    const response = await api.get('/v1/data-quality/metrics');
    return response.data;
  },
};
