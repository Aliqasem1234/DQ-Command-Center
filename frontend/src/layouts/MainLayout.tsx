import { useState } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import {
  Menu as MenuIcon,
  X as CloseIcon,
  LayoutDashboard as DashboardIcon,
  Building2 as DeptIcon,
  Users as PeopleIcon,
  Shield as RolesIcon,
  History as AuditIcon,
  User as ProfileIcon,
  Moon as DarkIcon,
  Sun as LightIcon,
  LogOut as LogoutIcon,
  CheckCircle as QualityIcon,
  Eye as MonitorIcon,
  ChevronDown as ChevronDownIcon,
  Database as DatasetsIcon,
} from 'lucide-react';
import { useThemeStore } from '../store/themeStore';
import { useAuthStore } from '../store/authStore';
import { useAuth } from '../hooks/useAuth';

const DRAWER_WIDTH = 260;

const menuItems = [
  { path: '/dashboard', label: 'nav.dashboard', icon: DashboardIcon },
  { path: '/datasets', label: 'nav.datasets', icon: DatasetsIcon },
  { path: '/data-quality/rules', label: 'dataQuality.rules', icon: QualityIcon },
  { path: '/data-quality/monitoring', label: 'dataQuality.monitoring', icon: MonitorIcon },
  { path: '/departments', label: 'nav.departments', icon: DeptIcon },
  { path: '/users', label: 'nav.users', icon: PeopleIcon },
  { path: '/roles', label: 'nav.roles', icon: RolesIcon },
  { path: '/audit', label: 'nav.audit', icon: AuditIcon },
];

export function MainLayout() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();
  const { mode, toggleTheme } = useThemeStore();
  const { user } = useAuthStore();
  const { logout } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [showUserMenu, setShowUserMenu] = useState(false);

  const handleDrawerToggle = () => setMobileOpen(!mobileOpen);
  const handleLanguageChange = (lng: string) => {
    i18n.changeLanguage(lng);
    document.documentElement.lang = lng;
  };

  const isActive = (path: string) =>
    location.pathname === path || location.pathname.startsWith(`${path}/`);

  const drawerContent = (
    <div className="flex flex-col h-full">
      <div className="p-4 text-center border-b border-slate-200">
        <h2 className="text-lg font-bold text-primary-600">DQ</h2>
      </div>
      <nav className="flex-1 overflow-y-auto">
        <ul className="space-y-1 p-2">
          {menuItems.map((item) => {
            const IconComponent = item.icon;
            return (
              <li key={item.path}>
                <button
                  onClick={() => {
                    navigate(item.path);
                    setMobileOpen(false);
                  }}
                  className={`w-full flex items-center gap-3 px-4 py-2 rounded-lg transition-colors ${
                    isActive(item.path)
                      ? 'bg-primary-100 text-primary-700'
                      : 'text-slate-700 hover:bg-slate-100'
                  }`}
                >
                  <IconComponent className="w-5 h-5" />
                  <span className="text-sm font-medium">{t(item.label)}</span>
                </button>
              </li>
            );
          })}
        </ul>
      </nav>
    </div>
  );

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Header */}
      <header className="fixed top-0 right-0 left-0 md:left-64 h-16 surface border-b shadow-sm z-40">
        <div className="h-full px-4 flex items-center justify-between">
          <button
            onClick={handleDrawerToggle}
            className="md:hidden p-2 hover:bg-slate-100 rounded-lg"
          >
            {mobileOpen ? (
              <CloseIcon className="w-5 h-5" />
            ) : (
              <MenuIcon className="w-5 h-5" />
            )}
          </button>

          <h1 className="text-lg font-bold text-slate-900 hidden md:block md:flex-1">
            {t('app.name')}
          </h1>

          <div className="flex items-center gap-3">
            {/* Language Selector */}
            <select
              value={i18n.language}
              onChange={(e) => handleLanguageChange(e.target.value)}
              className="px-2 py-1 text-sm border border-slate-300 rounded-lg bg-white hover:border-slate-400 focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              <option value="en">English</option>
              <option value="sv">Svenska</option>
            </select>

            {/* Theme Toggle */}
            <button
              onClick={toggleTheme}
              className="p-2 hover:bg-slate-100 rounded-lg transition-colors"
              title={t(mode === 'light' ? 'theme.dark' : 'theme.light')}
            >
              {mode === 'light' ? (
                <DarkIcon className="w-5 h-5" />
              ) : (
                <LightIcon className="w-5 h-5" />
              )}
            </button>

            {/* User Menu */}
            <div className="relative">
              <button
                onClick={() => setShowUserMenu(!showUserMenu)}
                className="flex items-center gap-2 px-3 py-2 hover:bg-slate-100 rounded-lg transition-colors"
              >
                <div className="w-7 h-7 bg-primary-600 rounded-full flex items-center justify-center text-white text-xs font-bold">
                  {user?.full_name?.charAt(0).toUpperCase() || 'U'}
                </div>
                <span className="text-sm font-medium text-slate-700 hidden sm:inline">
                  {user?.full_name}
                </span>
                <ChevronDownIcon className="w-4 h-4 text-slate-600" />
              </button>

              {/* User Dropdown Menu */}
              {showUserMenu && (
                <div className="absolute right-0 mt-2 w-48 surface border rounded-lg shadow-lg">
                  <div className="px-4 py-2 border-b border-slate-200 text-sm text-slate-600">
                    {user?.email}
                  </div>
                  <button
                    onClick={() => {
                      setShowUserMenu(false);
                      navigate('/profile');
                    }}
                    className="w-full text-left px-4 py-2 hover:bg-slate-50 text-sm text-slate-700 flex items-center gap-2"
                  >
                    <ProfileIcon className="w-4 h-4" />
                    {t('nav.settings')}
                  </button>
                  <button
                    onClick={() => {
                      setShowUserMenu(false);
                      logout();
                    }}
                    className="w-full text-left px-4 py-2 hover:bg-slate-50 text-sm text-slate-700 flex items-center gap-2 border-t border-slate-200"
                  >
                    <LogoutIcon className="w-4 h-4" />
                    {t('auth.logout')}
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Sidebar */}
      <aside className="hidden md:flex md:fixed left-0 top-0 bottom-0 w-64 surface border-r flex-col z-50 pt-16">
        {drawerContent}
      </aside>

      {/* Mobile Drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-30 md:hidden" onClick={handleDrawerToggle}>
          <aside className="w-64 h-full surface flex flex-col pt-16" onClick={(e) => e.stopPropagation()}>
            {drawerContent}
          </aside>
        </div>
      )}

      {/* Main Content */}
      <main className="flex-1 overflow-auto mt-16 md:ml-64">
        <div className="p-4 md:p-6">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
