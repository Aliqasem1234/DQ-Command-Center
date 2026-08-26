import { api } from './api';
import type {
  Role,
  RoleCreate,
  RoleUpdate,
  RoleListResponse,
  Permission,
  AssignPermissionsRequest,
} from '../types';

export const roleService = {
  async list(page = 1, pageSize = 20): Promise<RoleListResponse> {
    const response = await api.get<RoleListResponse>('/v1/roles', {
      params: { page, page_size: pageSize },
    });
    return response.data;
  },

  async listAll(): Promise<Role[]> {
    const response = await api.get<Role[]>('/v1/roles/all');
    return response.data;
  },

  async get(id: string): Promise<Role> {
    const response = await api.get<Role>(`/v1/roles/${id}`);
    return response.data;
  },

  async create(data: RoleCreate): Promise<Role> {
    const response = await api.post<Role>('/v1/roles', data);
    return response.data;
  },

  async update(id: string, data: RoleUpdate): Promise<Role> {
    const response = await api.put<Role>(`/v1/roles/${id}`, data);
    return response.data;
  },

  async delete(id: string): Promise<void> {
    await api.delete(`/v1/roles/${id}`);
  },

  async listPermissions(): Promise<Permission[]> {
    const response = await api.get<Permission[]>('/v1/permissions');
    return response.data;
  },

  async assignPermissions(id: string, data: AssignPermissionsRequest): Promise<Role> {
    const response = await api.put<Role>(`/v1/roles/${id}/permissions`, data);
    return response.data;
  },
};
