import { useAuthStore } from '../store/authStore';
import { hasPermission } from '../auth/permissions';

export function usePermission(code: string): boolean {
  const user = useAuthStore((s) => s.user);
  return hasPermission(user, code);
}
