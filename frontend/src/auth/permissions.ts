/**
 * Permission checks for the UI. These mirror the codes the backend enforces
 * (app.core.rbac.require_permission) and only decide what to *show*; the
 * backend independently authorizes every request.
 */
export const PERMISSIONS = {
  dashboardView: 'dashboard:view',
  datasetsView: 'datasets:view',
  datasetsManage: 'datasets:manage',
  qualityView: 'data_quality:view',
  qualityManage: 'data_quality:manage',
  governanceView: 'data_governance:view',
  governanceManage: 'data_governance:manage',
  usersManage: 'users:manage',
  rolesManage: 'roles:manage',
  departmentsManage: 'departments:manage',
  auditView: 'audit:view',
} as const;

interface PermissionSubject {
  is_super_admin?: boolean;
  permissions?: string[];
}

export function hasPermission(user: PermissionSubject | null | undefined, code: string): boolean {
  if (!user) return false;
  if (user.is_super_admin) return true;
  return Array.isArray(user.permissions) && user.permissions.includes(code);
}

export function hasAllPermissions(user: PermissionSubject | null | undefined, codes: readonly string[]): boolean {
  return codes.every((code) => hasPermission(user, code));
}
