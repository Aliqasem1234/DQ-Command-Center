import { api } from './api';
import type {
  GovernanceAssignment,
  GovernanceAssignmentCreate,
  GovernancePolicy,
  GovernancePolicyCreate,
  PaginatedResponse,
} from '../types';

export const governanceService = {
  async listAssignments(page = 1, pageSize = 50): Promise<PaginatedResponse<GovernanceAssignment>> {
    const response = await api.get<PaginatedResponse<GovernanceAssignment>>('/v1/governance/assignments', {
      params: { page, page_size: pageSize },
    });
    return response.data;
  },

  async createAssignment(data: GovernanceAssignmentCreate): Promise<GovernanceAssignment> {
    const response = await api.post<GovernanceAssignment>('/v1/governance/assignments', data);
    return response.data;
  },

  async revokeAssignment(id: string): Promise<void> {
    await api.delete(`/v1/governance/assignments/${id}`);
  },

  async listPolicies(page = 1, pageSize = 50): Promise<PaginatedResponse<GovernancePolicy>> {
    const response = await api.get<PaginatedResponse<GovernancePolicy>>('/v1/governance/policies', {
      params: { page, page_size: pageSize },
    });
    return response.data;
  },

  async createPolicy(data: GovernancePolicyCreate): Promise<GovernancePolicy> {
    const response = await api.post<GovernancePolicy>('/v1/governance/policies', data);
    return response.data;
  },

  async deletePolicy(id: string): Promise<void> {
    await api.delete(`/v1/governance/policies/${id}`);
  },
};
