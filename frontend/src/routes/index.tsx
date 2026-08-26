import { createBrowserRouter, Navigate } from 'react-router-dom';
import { AuthLayout } from '../layouts/AuthLayout';
import { MainLayout } from '../layouts/MainLayout';
import { ProtectedRoute } from './ProtectedRoute';
import { LoginPageModern as LoginPage } from '../pages/auth/LoginPageModern';
import { RegisterPage } from '../pages/auth/RegisterPage';
import { ForgotPasswordPage } from '../pages/auth/ForgotPasswordPage';
import { ResetPasswordPage } from '../pages/auth/ResetPasswordPage';
import { VerifyEmailPage } from '../pages/auth/VerifyEmailPage';
import { DashboardPageModern as DashboardPage } from '../pages/dashboard/DashboardPageModern';
import { DepartmentListPage } from '../pages/departments/DepartmentListPage';
import { UserListPage } from '../pages/users/UserListPage';
import { RoleListPage } from '../pages/roles/RoleListPage';
import { AuditLogPage } from '../pages/audit/AuditLogPage';
import { ProfilePage } from '../pages/profile/ProfilePage';
import { NotFoundPage } from '../pages/errors/NotFoundPage';
import { ForbiddenPage } from '../pages/errors/ForbiddenPage';
import DataQualityRulesPage from '../pages/dataQuality/DataQualityRulesPage';
import DataQualityMonitoringPage from '../pages/dataQuality/DataQualityMonitoringPage';
import { DatasetsListPage } from '../pages/datasets/DatasetsListPage';
import { DatasetDetailPage } from '../pages/datasets/DatasetDetailPage';

export const router = createBrowserRouter([
  {
    path: '/',
    element: <AuthLayout />,
    children: [
      { index: true, element: <Navigate to="/login" replace /> },
      { path: 'login', element: <LoginPage /> },
      { path: 'register', element: <RegisterPage /> },
      { path: 'forgot-password', element: <ForgotPasswordPage /> },
      { path: 'reset-password', element: <ResetPasswordPage /> },
      { path: 'verify-email', element: <VerifyEmailPage /> },
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
      { path: 'dashboard', element: <DashboardPage /> },
      { path: 'datasets', element: <DatasetsListPage /> },
      { path: 'datasets/:datasetId', element: <DatasetDetailPage /> },
      { path: 'departments', element: <DepartmentListPage /> },
      { path: 'users', element: <UserListPage /> },
      { path: 'roles', element: <RoleListPage /> },
      { path: 'audit', element: <AuditLogPage /> },
      { path: 'profile', element: <ProfilePage /> },
      { path: 'data-quality/rules', element: <DataQualityRulesPage /> },
      { path: 'data-quality/monitoring', element: <DataQualityMonitoringPage /> },
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
