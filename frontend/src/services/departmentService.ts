import { api } from './api';
import type {
  Department,
  DepartmentCreate,
  DepartmentUpdate,
  DepartmentListResponse,
} from '../types';

export const departmentService = {
  async list(page = 1, pageSize = 20, search?: string): Promise<DepartmentListResponse> {
    const params: Record<string, string | number> = { page, page_size: pageSize };
    if (search) params.search = search;
    const response = await api.get<DepartmentListResponse>('/v1/departments', { params });
    return response.data;
  },

  async listAll(): Promise<{ id: string; name: string }[]> {
    const response = await api.get<{ id: string; name: string }[]>('/v1/departments/all');
    return response.data;
  },

  async get(id: string): Promise<Department> {
    const response = await api.get<Department>(`/v1/departments/${id}`);
    return response.data;
  },

  async create(data: DepartmentCreate): Promise<Department> {
    const response = await api.post<Department>('/v1/departments', data);
    return response.data;
  },

  async update(id: string, data: DepartmentUpdate): Promise<Department> {
    const response = await api.put<Department>(`/v1/departments/${id}`, data);
    return response.data;
  },

  async delete(id: string): Promise<void> {
    await api.delete(`/v1/departments/${id}`);
  },
};
