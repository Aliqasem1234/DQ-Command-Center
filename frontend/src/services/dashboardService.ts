import { api } from './api';
import type { DashboardResponse, DashboardHealthSummary, QualityIssueSummary } from '../types';

export const dashboardService = {
  async getStats(): Promise<DashboardResponse> {
    const response = await api.get<DashboardResponse>('/v1/dashboard/stats');
    return response.data;
  },

  async getHealthSummary(days = 30): Promise<DashboardHealthSummary> {
    const response = await api.get<DashboardHealthSummary>('/v1/dashboard/summary', {
      params: { days },
    });
    return response.data;
  },

  async getOpenIssues(limit = 10): Promise<QualityIssueSummary[]> {
    const response = await api.get<QualityIssueSummary[]>('/v1/quality-issues/open', {
      params: { limit },
    });
    return response.data;
  },
};
