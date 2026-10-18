import { useEffect, useMemo, type ReactNode } from 'react';
import { QueryClientProvider } from '@tanstack/react-query';
import { useAuthStore } from '../store/authStore';
import { createQueryClient } from './client';

const AUTH_STORAGE_KEY = 'dq-auth-storage';

/**
 * Scopes all server data to the signed-in identity.
 *
 * When the user changes (login, logout, a failed token refresh, or a switch
 * made in another tab) a brand-new QueryClient is created and the old one is
 * cleared, and the tree below remounts so components holding fetched data in
 * local state fetch again too. Nothing cached for one account can be shown to
 * the next, and late responses to the previous user's in-flight requests land
 * in the discarded client.
 */
export function IdentityScopedQueryProvider({ children }: { children: ReactNode }) {
  const identity = useAuthStore((s) => s.user?.id ?? 'signed-out');
  const client = useMemo(() => createQueryClient(), [identity]);

  useEffect(() => () => client.clear(), [client]);

  // Another tab signed in as someone else or signed out: adopt its session
  // instead of carrying on as a stale identity in this tab.
  useEffect(() => {
    const onStorage = (event: StorageEvent) => {
      if (event.key === AUTH_STORAGE_KEY) void useAuthStore.persist.rehydrate();
    };
    window.addEventListener('storage', onStorage);
    return () => window.removeEventListener('storage', onStorage);
  }, []);

  return (
    <QueryClientProvider client={client} key={identity}>
      {children}
    </QueryClientProvider>
  );
}
