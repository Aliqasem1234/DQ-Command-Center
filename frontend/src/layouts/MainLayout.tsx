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
  Landmark as GovernanceIcon,
  Activity as BrandIcon,
} from 'lucide-react';
import { useThemeStore } from '../store/themeStore';
import { useAuthStore } from '../store/authStore';
import { useAuth } from '../hooks/useAuth';

interface NavItem {
  path: string;
  label: string;
  icon: typeof DashboardIcon;
}

interface NavSection {
  label: string | null;
  items: NavItem[];
}

const navSections: NavSection[] = [
  {
    label: null,
    items: [{ path: '/dashboard', label: 'nav.dashboard', icon: DashboardIcon }],
  },
  {
    label: 'nav.sectionData',
    items: [{ path: '/datasets', label: 'nav.datasets', icon: DatasetsIcon }],
  },
  {
    label: 'nav.sectionQuality',
    items: [
      { path: '/data-quality/rules', label: 'dataQuality.rules', icon: QualityIcon },
      { path: '/data-quality/monitoring', label: 'dataQuality.monitoring', icon: MonitorIcon },
      { path: '/governance', label: 'nav.governance', icon: GovernanceIcon },
    ],
  },
  {
    label: 'nav.sectionAdmin',
    items: [
      { path: '/departments', label: 'nav.departments', icon: DeptIcon },
      { path: '/users', label: 'nav.users', icon: PeopleIcon },
      { path: '/roles', label: 'nav.roles', icon: RolesIcon },
      { path: '/audit', label: 'nav.audit', icon: AuditIcon },
    ],
  },
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

  const primaryRole = user?.is_super_admin ? t('profile.superAdmin') : user?.roles?.[0];

  const drawerContent = (
    <div className="flex flex-col h-full">
      <div className="h-16 flex items-center gap-2.5 px-5 border-b border-slate-200 dark:border-slate-800 flex-shrink-0">
        <div className="w-8 h-8 rounded-lg bg-primary-600 flex items-center justify-center flex-shrink-0 shadow-sm">
          <BrandIcon className="w-4.5 h-4.5 text-white" size={18} />
        </div>
        <div className="min-w-0 leading-tight">
          <p className="text-sm font-bold text-slate-900 truncate">{t('app.name')}</p>
        </div>
      </div>
      <nav className="flex-1 overflow-y-auto px-3 py-4">
        {navSections.map((section, i) => (
          <div key={i} className={i > 0 ? 'mt-6' : ''}>
            {section.label && (
              <p className="px-3 mb-2 text-[11px] font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider">
                {t(section.label)}
              </p>
            )}
            <ul className="space-y-0.5">
              {section.items.map((item) => {
                const IconComponent = item.icon;
                const active = isActive(item.path);
                return (
                  <li key={item.path}>
                    <button
                      onClick={() => {
                        navigate(item.path);
                        setMobileOpen(false);
                      }}
                      className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-all ${
                        active
                          ? 'bg-primary-600 text-white shadow-sm'
                          : 'text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 hover:text-slate-900 dark:hover:text-slate-50'
                      }`}
                    >
                      <IconComponent className="w-[18px] h-[18px] flex-shrink-0" />
                      <span className="truncate">{t(item.label)}</span>
                    </button>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </nav>
    </div>
  );

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Header */}
      <header className="fixed top-0 right-0 left-0 md:left-64 h-16 surface border-b z-40">
        <div className="h-full px-4 md:px-6 flex items-center justify-between">
          <button
            onClick={handleDrawerToggle}
            className="md:hidden icon-btn"
            aria-label={mobileOpen ? t('common.closeMenu') : t('common.openMenu')}
          >
            {mobileOpen ? (
              <CloseIcon className="w-5 h-5" />
            ) : (
              <MenuIcon className="w-5 h-5" />
            )}
          </button>

          <div className="hidden md:block" />

          <div className="flex items-center gap-1.5">
            {/* Language Selector */}
            <select
              value={i18n.language}
              onChange={(e) => handleLanguageChange(e.target.value)}
              aria-label={t('language.select')}
              className="input-base w-auto py-1.5 pl-2.5 pr-7 text-sm border-transparent bg-transparent hover:bg-slate-100 dark:hover:bg-slate-800 focus:border-slate-300 dark:focus:border-slate-700 cursor-pointer"
            >
              <option value="en">{t('language.en')}</option>
              <option value="sv">{t('language.sv')}</option>
            </select>

            {/* Theme Toggle */}
            <button
              onClick={toggleTheme}
              className="icon-btn"
              title={t(mode === 'light' ? 'theme.dark' : 'theme.light')}
              aria-label={t(mode === 'light' ? 'theme.dark' : 'theme.light')}
            >
              {mode === 'light' ? (
                <DarkIcon className="w-[18px] h-[18px]" />
              ) : (
                <LightIcon className="w-[18px] h-[18px]" />
              )}
            </button>

            <div className="w-px h-6 bg-slate-200 dark:bg-slate-800 mx-1" />

            {/* User Menu */}
            <div className="relative">
              <button
                onClick={() => setShowUserMenu(!showUserMenu)}
                className="flex items-center gap-2.5 pl-1 pr-2.5 py-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                aria-haspopup="true"
                aria-expanded={showUserMenu}
                aria-label={user?.full_name}
              >
                <div className="w-8 h-8 rounded-full bg-primary-600 flex items-center justify-center text-white text-xs font-bold flex-shrink-0 ring-2 ring-white dark:ring-slate-900">
                  {user?.full_name?.charAt(0).toUpperCase() || 'U'}
                </div>
                <div className="hidden sm:block text-left leading-tight">
                  <p className="text-sm font-semibold text-slate-800 dark:text-slate-100">
                    {user?.full_name}
                  </p>
                  {primaryRole && (
                    <p className="text-xs text-slate-500 dark:text-slate-400">{primaryRole}</p>
                  )}
                </div>
                <ChevronDownIcon className="w-4 h-4 text-slate-400 hidden sm:block" />
              </button>

              {/* User Dropdown Menu */}
              {showUserMenu && (
                <>
                  <div className="fixed inset-0 z-40" onClick={() => setShowUserMenu(false)} />
                  <div className="absolute right-0 mt-2 w-56 surface border rounded-xl shadow-lg z-50 overflow-hidden py-1">
                    <div className="px-4 py-3 border-b border-slate-100 dark:border-slate-800">
                      <p className="text-sm font-semibold text-slate-800 dark:text-slate-100 truncate">{user?.full_name}</p>
                      <p className="text-xs text-slate-500 dark:text-slate-400 truncate">{user?.email}</p>
                    </div>
                    <button
                      onClick={() => {
                        setShowUserMenu(false);
                        navigate('/profile');
                      }}
                      className="w-full text-left px-4 py-2.5 hover:bg-slate-50 dark:hover:bg-slate-800 text-sm text-slate-700 dark:text-slate-200 flex items-center gap-2.5"
                    >
                      <ProfileIcon className="w-4 h-4 text-slate-400" />
                      {t('nav.settings')}
                    </button>
                    <div className="my-1 border-t border-slate-100 dark:border-slate-800" />
                    <button
                      onClick={() => {
                        setShowUserMenu(false);
                        logout();
                      }}
                      className="w-full text-left px-4 py-2.5 hover:bg-red-50 dark:hover:bg-red-500/10 text-sm text-red-600 dark:text-red-400 flex items-center gap-2.5"
                    >
                      <LogoutIcon className="w-4 h-4" />
                      {t('auth.logout')}
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Sidebar */}
      <aside className="hidden md:flex md:fixed left-0 top-0 bottom-0 w-64 surface border-r flex-col z-50">
        {drawerContent}
      </aside>

      {/* Mobile Drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 bg-black/50 z-30 md:hidden" onClick={handleDrawerToggle}>
          <aside className="w-64 h-full surface flex flex-col" onClick={(e) => e.stopPropagation()}>
            {drawerContent}
          </aside>
        </div>
      )}

      {/* Main Content */}
      <main className="flex-1 overflow-auto mt-16 md:ml-64 bg-slate-50 dark:bg-slate-950">
        <div className="max-w-[1600px] mx-auto p-4 md:p-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
