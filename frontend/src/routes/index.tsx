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

// Everything reachable only after login (or as a secondary auth flow) is
// lazy-loaded so the initial bundle only carries the login screen - the
// production build otherwise bundled every page (dashboard, datasets,
// governance, quality rules, etc.) into one >900KB chunk regardless of
// which page a given user actually needed.
const RegisterPage = lazy(() => import('../pages/auth/RegisterPage').then((m) => ({ default: m.RegisterPage })));
const ResetPasswordPage = lazy(() => import('../pages/auth/ResetPasswordPage').then((m) => ({ default: m.ResetPasswordPage })));
const VerifyEmailPage = lazy(() => import('../pages/auth/VerifyEmailPage').then((m) => ({ default: m.VerifyEmailPage })));
const DashboardPage = lazy(() => import('../pages/dashboard/DashboardPageModern').then((m) => ({ default: m.DashboardPageModern })));
const DepartmentListPage = lazy(() => import('../pages/departments/DepartmentListPage').then((m) => ({ default: m.DepartmentListPage })));
const UserListPage = lazy(() => import('../pages/users/UserListPage').then((m) => ({ default: m.UserListPage })));
const RoleListPage = lazy(() => import('../pages/roles/RoleListPage').then((m) => ({ default: m.RoleListPage })));
const AuditLogPage = lazy(() => import('../pages/audit/AuditLogPage').then((m) => ({ default: m.AuditLogPage })));
const ProfilePage = lazy(() => import('../pages/profile/ProfilePage').then((m) => ({ default: m.ProfilePage })));
const DataQualityRulesPage = lazy(() => import('../pages/dataQuality/DataQualityRulesPage'));
const DataQualityMonitoringPage = lazy(() => import('../pages/dataQuality/DataQualityMonitoringPage'));
const DatasetsListPage = lazy(() => import('../pages/datasets/DatasetsListPage').then((m) => ({ default: m.DatasetsListPage })));
const DatasetDetailPage = lazy(() => import('../pages/datasets/DatasetDetailPage').then((m) => ({ default: m.DatasetDetailPage })));
const GovernancePage = lazy(() => import('../pages/governance/GovernancePage').then((m) => ({ default: m.GovernancePage })));

function Loadable({ children }: { children: ReactNode }) {
  return <Suspense fallback={<LoadingSpinner />}>{children}</Suspense>;
}

export const router = createBrowserRouter([
  {
    path: '/',
    element: <AuthLayout />,
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
    children: [
      { path: 'dashboard', element: <Loadable><DashboardPage /></Loadable> },
      { path: 'datasets', element: <Loadable><DatasetsListPage /></Loadable> },
      { path: 'datasets/:datasetId', element: <Loadable><DatasetDetailPage /></Loadable> },
      { path: 'governance', element: <Loadable><GovernancePage /></Loadable> },
      { path: 'departments', element: <Loadable><DepartmentListPage /></Loadable> },
      { path: 'users', element: <Loadable><UserListPage /></Loadable> },
      { path: 'roles', element: <Loadable><RoleListPage /></Loadable> },
      { path: 'audit', element: <Loadable><AuditLogPage /></Loadable> },
      { path: 'profile', element: <Loadable><ProfilePage /></Loadable> },
      { path: 'data-quality/rules', element: <Loadable><DataQualityRulesPage /></Loadable> },
      { path: 'data-quality/monitoring', element: <Loadable><DataQualityMonitoringPage /></Loadable> },
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
