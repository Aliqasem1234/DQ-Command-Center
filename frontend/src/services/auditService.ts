import { api } from './api';
import type { AuditLogListResponse } from '../types';

export const auditService = {
  async list(
    page = 1,
    pageSize = 50,
    entityType?: string,
    action?: string,
  ): Promise<AuditLogListResponse> {
    const params: Record<string, string | number> = { page, page_size: pageSize };
    if (entityType) params.entity_type = entityType;
    if (action) params.action = action;
    const response = await api.get<AuditLogListResponse>('/v1/audit/logs', { params });
    return response.data;
  },
};
