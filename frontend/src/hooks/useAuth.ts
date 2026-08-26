import { useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { authService } from '../services/authService';
import { getErrorMessage } from '../services/api';
import type { LoginRequest, RegisterRequest } from '../types';

export function useAuth() {
  const navigate = useNavigate();
  const { setAuth, clearAuth, user, isAuthenticated } = useAuthStore();

  const login = useCallback(
    async (data: LoginRequest) => {
      try {
        const response = await authService.login(data);
        setAuth(response.user, response.access_token, response.refresh_token);
        navigate('/dashboard');
        return { success: true };
      } catch (error) {
        return { success: false, error: getErrorMessage(error) };
      }
    },
    [setAuth, navigate]
  );

  const register = useCallback(async (data: RegisterRequest) => {
    try {
      const response = await authService.register(data);
      return { success: true, message: response.message };
    } catch (error) {
      return { success: false, error: getErrorMessage(error) };
    }
  }, []);

  const logout = useCallback(async () => {
    try {
      const refreshToken = useAuthStore.getState().refreshToken;
      if (refreshToken) {
        await authService.logout(refreshToken);
      }
    } catch {
      // Ignore logout errors
    } finally {
      clearAuth();
      navigate('/login');
    }
  }, [clearAuth, navigate]);

  const forgotPassword = useCallback(async (email: string) => {
    try {
      const response = await authService.forgotPassword(email);
      return { success: true, message: response.message };
    } catch (error) {
      return { success: false, error: getErrorMessage(error) };
    }
  }, []);

  const resetPassword = useCallback(
    async (token: string, password: string) => {
      try {
        const response = await authService.resetPassword({ token, password });
        navigate('/login');
        return { success: true, message: response.message };
      } catch (error) {
        return { success: false, error: getErrorMessage(error) };
      }
    },
    [navigate]
  );

  const verifyEmail = useCallback(async (token: string) => {
    try {
      const response = await authService.verifyEmail(token);
      return { success: true, message: response.message };
    } catch (error) {
      return { success: false, error: getErrorMessage(error) };
    }
  }, []);

  return {
    user,
    isAuthenticated,
    login,
    register,
    logout,
    forgotPassword,
    resetPassword,
    verifyEmail,
  };
}
