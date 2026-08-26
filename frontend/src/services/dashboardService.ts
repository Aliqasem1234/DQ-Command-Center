import { api } from './api';
import type { DashboardResponse } from '../types';

export const dashboardService = {
  async getStats(): Promise<DashboardResponse> {
    const response = await api.get<DashboardResponse>('/v1/dashboard/stats');
    return response.data;
  },
};
