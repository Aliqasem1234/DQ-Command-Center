import { api } from './api';
import type {
  User,
  UserCreate,
  UserUpdate,
  UserListResponse,
  AssignRolesRequest,
} from '../types';

export const userService = {
  async list(page = 1, pageSize = 20, search?: string): Promise<UserListResponse> {
    const params: Record<string, string | number> = { page, page_size: pageSize };
    if (search) params.search = search;
    const response = await api.get<UserListResponse>('/v1/users', { params });
    return response.data;
  },

  async get(id: string): Promise<User> {
    const response = await api.get<User>(`/v1/users/${id}`);
    return response.data;
  },

  async create(data: UserCreate): Promise<User> {
    const response = await api.post<User>('/v1/users', data);
    return response.data;
  },

  async update(id: string, data: UserUpdate): Promise<User> {
    const response = await api.put<User>(`/v1/users/${id}`, data);
    return response.data;
  },

  async assignRoles(id: string, data: AssignRolesRequest): Promise<User> {
    const response = await api.put<User>(`/v1/users/${id}/roles`, data);
    return response.data;
  },

  async deactivate(id: string): Promise<void> {
    await api.delete(`/v1/users/${id}`);
  },
};
