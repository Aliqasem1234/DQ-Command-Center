// @vitest-environment jsdom
/**
 * Regression test for the cross-user leak reported on 2026-10-18: after one
 * account signed out and another signed in on the same tab, pages showed
 * the previous account's cached data (no request was even made), because
 * query keys like ['all-datasets'] are not user-specific and the cache was
 * shared across identities.
 */
import { describe, it, expect, beforeEach } from 'vitest';
import { render, act, cleanup } from '@testing-library/react';
import { useQueryClient, type QueryClient } from '@tanstack/react-query';
import { IdentityScopedQueryProvider } from '../IdentityScopedQueryProvider';
import { useAuthStore, type User } from '../../store/authStore';

const person = (id: string): User => ({
  id, email: `${id}@example.com`, username: id, full_name: id, department: null, department_id: null,
  department_name: null, is_active: true, is_verified: true, is_super_admin: false, created_at: '', roles: ['User'],
  permissions: [],
});

let current: QueryClient | null = null;
function Probe() {
  current = useQueryClient();
  return null;
}

describe('IdentityScopedQueryProvider', () => {
  beforeEach(() => {
    cleanup();
    current = null;
    useAuthStore.getState().clearAuth();
  });

  it('never serves one account\'s cached data to the next account', () => {
    act(() => useAuthStore.getState().setAuth(person('admin'), 'a', 'r'));
    render(<IdentityScopedQueryProvider><Probe /></IdentityScopedQueryProvider>);
    const adminClient = current!;
    adminClient.setQueryData(['all-datasets'], [{ name: 'QA kunder (admin)' }]);

    act(() => useAuthStore.getState().clearAuth()); // log out
    act(() => useAuthStore.getState().setAuth(person('regular'), 'b', 'r')); // next person logs in

    expect(current).not.toBe(adminClient);
    expect(current!.getQueryData(['all-datasets'])).toBeUndefined();
    // The previous account's cache is wiped, so late responses can't resurface.
    expect(adminClient.getQueryData(['all-datasets'])).toBeUndefined();
  });

  it('keeps the cache while the same account stays signed in (profile refresh)', () => {
    act(() => useAuthStore.getState().setAuth(person('alice'), 'a', 'r'));
    render(<IdentityScopedQueryProvider><Probe /></IdentityScopedQueryProvider>);
    const client = current!;
    client.setQueryData(['all-datasets'], [{ name: 'mine' }]);

    act(() => useAuthStore.getState().setUser({ ...person('alice'), full_name: 'Alice Renamed' }));

    expect(current).toBe(client);
    expect(current!.getQueryData(['all-datasets'])).toEqual([{ name: 'mine' }]);
  });
});
