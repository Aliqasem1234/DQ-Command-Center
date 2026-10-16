import { lazy, Suspense, type ReactNode } from 'react';
import { createBrowserRouter, Navigate } from 'react-router-dom';
import { AuthLayout } from '../layouts/AuthLayout';
import { MainLayout } from '../layouts/MainLayout';
import { ProtectedRoute } from './ProtectedRoute';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { LoginPageModern as LoginPage } from '../pages/auth/LoginPageModern';
import { ForgotPasswordPage } from '../pages/auth/ForgotPasswordPage';
import { NotFoundPage } from '../pages/errors/NotFoundPage';
import { ForbiddenPage } from '../pages/errors/ForbiddenPage';
import { RouteErrorPage } from '../pages/errors/RouteErrorPage';
import { PERMISSIONS as P } from '../auth/permissions';

// Lazy-load all protected pages for better initial bundle performance
const RegisterPage = lazy(() => import('../pages/auth/RegisterPage').then((m) => ({ default: m.RegisterPage })));
const ResetPasswordPage = lazy(() => import('../pages/auth/ResetPasswordPage').then((m) => ({ default: m.ResetPasswordPage })));
const VerifyEmailPage = lazy(() => import('../pages/auth/VerifyEmailPage').then((m) => ({ default: m.VerifyEmailPage })));
const DashboardPage = lazy(() => import('../pages/dashboard/DashboardPageModern').then((m) => ({ default: m.DashboardPageModern })));
const DepartmentListPage = lazy(() => import('../pages/departments/DepartmentListPage').then((m) => ({ default: m.DepartmentListPage })));
const UserListPage = lazy(() => import('../pages/users/UserListPage').then((m) => ({ default: m.UserListPage })));
const RoleListPage = lazy(() => import('../pages/roles/RoleListPage').then((m) => ({ default: m.RoleListPage })));
const AuditLogPage = lazy(() => import('../pages/audit/AuditLogPage').then((m) => ({ default: m.AuditLogPage })));
const ProfilePage = lazy(() => import('../pages/profile/ProfilePage').then((m) => ({ default: m.ProfilePage })));
const SecurityPage = lazy(() => import('../pages/profile/SecurityPage').then((m) => ({ default: m.SecurityPage })));
const DataQualityRulesPage = lazy(() => import('../pages/dataQuality/DataQualityRulesPage'));
const DataQualityMonitoringPage = lazy(() => import('../pages/dataQuality/DataQualityMonitoringPage'));
const DatasetsListPage = lazy(() => import('../pages/datasets/DatasetsListPage').then((m) => ({ default: m.DatasetsListPage })));
const DatasetDetailPage = lazy(() => import('../pages/datasets/DatasetDetailPage').then((m) => ({ default: m.DatasetDetailPage })));
const GovernancePage = lazy(() => import('../pages/governance/GovernancePage').then((m) => ({ default: m.GovernancePage })));

function Loadable({ children }: { children: ReactNode }) {
  return <Suspense fallback={<LoadingSpinner />}>{children}</Suspense>;
}

function guarded(path: string, page: ReactNode, permissions: readonly string[]) {
  return {
    path,
    element: (
      <ProtectedRoute requiredPermissions={permissions}>
        <Loadable>{page}</Loadable>
      </ProtectedRoute>
    ),
  };
}

export const router = createBrowserRouter([
  {
    path: '/',
    element: <AuthLayout />,
    errorElement: <RouteErrorPage />,
    children: [
      { index: true, element: <Navigate to="/login" replace /> },
      { path: 'login', element: <LoginPage /> },
      { path: 'register', element: <Loadable><RegisterPage /></Loadable> },
      { path: 'forgot-password', element: <ForgotPasswordPage /> },
      { path: 'reset-password', element: <Loadable><ResetPasswordPage /></Loadable> },
      { path: 'verify-email', element: <Loadable><VerifyEmailPage /></Loadable> },
    ],
  },
  {
    path: '/',
    element: (
      <ProtectedRoute>
        <MainLayout />
      </ProtectedRoute>
    ),
    errorElement: <RouteErrorPage />,
    children: [
      { path: 'dashboard', element: <Loadable><DashboardPage /></Loadable> },
      { path: 'profile', element: <Loadable><ProfilePage /></Loadable> },
      { path: 'security', element: <Loadable><SecurityPage /></Loadable> },
      { path: 'activity', element: <Loadable><AuditLogPage scope="mine" /></Loadable> },
      guarded('datasets', <DatasetsListPage />, [P.datasetsView]),
      guarded('datasets/:datasetId', <DatasetDetailPage />, [P.datasetsView]),
      guarded('governance', <GovernancePage />, [P.governanceView]),
      guarded('data-quality/rules', <DataQualityRulesPage />, [P.qualityView]),
      guarded('data-quality/monitoring', <DataQualityMonitoringPage />, [P.qualityView]),
      // Admin pages: gated on the exact permission each page's API requires.
      guarded('users', <UserListPage />, [P.usersManage]),
      guarded('roles', <RoleListPage />, [P.rolesManage]),
      guarded('departments', <DepartmentListPage />, [P.departmentsManage]),
      guarded('audit', <AuditLogPage scope="system" />, [P.auditView]),
    ],
  },
  {
    path: '/forbidden',
    element: <ForbiddenPage />,
  },
  {
    path: '*',
    element: <NotFoundPage />,
  },
]);
