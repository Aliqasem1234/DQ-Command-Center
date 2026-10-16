import { Navigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { hasAllPermissions } from '../auth/permissions';
import { LoadingSpinner } from '../components/common/LoadingSpinner';

interface ProtectedRouteProps {
  children: React.ReactNode;
  requiredPermissions?: readonly string[];
}

/**
 * Requires a signed-in user and, optionally, permission codes.
 *
 * Route guards improve UX but are NOT a security boundary - the backend
 * authorizes every API request independently.
 */
export function ProtectedRoute({ children, requiredPermissions = [] }: ProtectedRouteProps) {
  const { isAuthenticated, user } = useAuthStore();
  const location = useLocation();

  if (!isAuthenticated || !user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (requiredPermissions.length > 0) {
    // A session persisted before permissions were part of the user payload
    // is refreshed from /auth/me by MainLayout; wait for it rather than
    // bouncing an authorized user to /forbidden.
    if (!user.is_super_admin && user.permissions === undefined) {
      return <LoadingSpinner />;
    }
    if (!hasAllPermissions(user, requiredPermissions)) {
      return <Navigate to="/forbidden" replace />;
    }
  }

  return <>{children}</>;
}
