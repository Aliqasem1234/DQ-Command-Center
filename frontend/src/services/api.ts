import axios, {
  AxiosError,
  InternalAxiosRequestConfig,
  AxiosResponse,
} from 'axios';
import { useAuthStore } from '../store/authStore';
import { normalizeError } from './errorNormalizer';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,
});

// A 401 from these means "wrong credentials/token", not "access token
// expired", so it must reach the caller instead of triggering a refresh.
// (Request URLs are relative to baseURL, e.g. "/v1/auth/login".)
const PUBLIC_AUTH_PATHS = ['login', 'register', 'refresh', 'forgot-password', 'reset-password', 'verify-email'];

export function isPublicAuthRequest(url: string | undefined): boolean {
  if (!url) return false;
  const path = url.split('?')[0];
  return PUBLIC_AUTH_PATHS.some((p) => path.endsWith(`/v1/auth/${p}`));
}

let isRefreshing = false;
let failedQueue: Array<{
  resolve: (token: string) => void;
  reject: (error: unknown) => void;
}> = [];

const processQueue = (error: unknown, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else if (token) {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const { accessToken } = useAuthStore.getState();
    if (accessToken && config.headers) {
      config.headers.Authorization = `Bearer ${accessToken}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

api.interceptors.response.use(
  (response: AxiosResponse) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & {
      _retry?: boolean;
    };

    if (
      error.response?.status === 401 &&
      originalRequest &&
      !originalRequest._retry &&
      !isPublicAuthRequest(originalRequest.url)
    ) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({
            resolve: (token: string) => {
              if (originalRequest.headers) {
                originalRequest.headers.Authorization = `Bearer ${token}`;
              }
              resolve(api(originalRequest));
            },
            reject,
          });
        });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      const { refreshToken } = useAuthStore.getState();

      if (!refreshToken) {
        useAuthStore.getState().clearAuth();
        isRefreshing = false;
        return Promise.reject(error);
      }

      try {
        const response = await axios.post(
          `${API_BASE_URL}/v1/auth/refresh`,
          { refresh_token: refreshToken }
        );

        const { access_token, refresh_token } = response.data;
        useAuthStore.getState().setTokens(access_token, refresh_token);

        processQueue(null, access_token);

        if (originalRequest.headers) {
          originalRequest.headers.Authorization = `Bearer ${access_token}`;
        }
        return api(originalRequest);
      } catch (refreshError) {
        processQueue(refreshError, null);
        useAuthStore.getState().clearAuth();
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

/**
 * Converts any thrown value into a readable message in the user's language.
 * Always returns a string, so it is always safe to render.
 */
export function getErrorMessage(error: unknown): string {
  return normalizeError(error);
}
