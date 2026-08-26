import { api } from './api';
import type {
  LoginRequest,
  LoginResponse,
  RegisterRequest,
  MessageResponse,
  RefreshTokenResponse,
  ResetPasswordRequest,
  ChangePasswordRequest,
  UserResponse,
} from '../types';

export const authService = {
  async login(data: LoginRequest): Promise<LoginResponse> {
    const response = await api.post<LoginResponse>('/v1/auth/login', data);
    return response.data;
  },

  async register(data: RegisterRequest): Promise<MessageResponse> {
    const response = await api.post<MessageResponse>('/v1/auth/register', data);
    return response.data;
  },

  async refresh(refreshToken: string): Promise<RefreshTokenResponse> {
    const response = await api.post<RefreshTokenResponse>('/v1/auth/refresh', {
      refresh_token: refreshToken,
    });
    return response.data;
  },

  async logout(refreshToken: string): Promise<MessageResponse> {
    const response = await api.post<MessageResponse>('/v1/auth/logout', {
      refresh_token: refreshToken,
    });
    return response.data;
  },

  async forgotPassword(email: string): Promise<MessageResponse> {
    const response = await api.post<MessageResponse>('/v1/auth/forgot-password', {
      email,
    });
    return response.data;
  },

  async resetPassword(data: ResetPasswordRequest): Promise<MessageResponse> {
    const response = await api.post<MessageResponse>('/v1/auth/reset-password', data);
    return response.data;
  },

  async verifyEmail(token: string): Promise<MessageResponse> {
    const response = await api.post<MessageResponse>('/v1/auth/verify-email', {
      token,
    });
    return response.data;
  },

  async changePassword(data: ChangePasswordRequest): Promise<MessageResponse> {
    const response = await api.post<MessageResponse>('/v1/auth/change-password', data);
    return response.data;
  },

  async getCurrentUser(): Promise<UserResponse> {
    const response = await api.get<UserResponse>('/v1/auth/me');
    return response.data;
  },
};
