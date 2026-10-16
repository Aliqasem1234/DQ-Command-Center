import { QueryClient } from '@tanstack/react-query';
import { isAxiosError } from 'axios';

// Retry once for transient failures (network, 5xx) but never for 4xx: a
// 403/404/422 will answer the same way again, and retrying only doubles the
// requests and delays the error message.
function shouldRetry(failureCount: number, error: unknown): boolean {
  const status = isAxiosError(error) ? error.response?.status : undefined;
  if (status !== undefined && status >= 400 && status < 500) return false;
  return failureCount < 1;
}

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: shouldRetry,
      refetchOnWindowFocus: false,
      staleTime: 5 * 60 * 1000,
      gcTime: 10 * 60 * 1000,
    },
    mutations: {
      retry: 0,
    },
  },
});
