import { NavLink, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  Phone,
  Users,
  Music,
  Settings,
  GitBranch,
  LogOut,
  ChevronRight,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useAuth } from '@/hooks/use-auth';
import { usePermissions, Permission } from '@/hooks/use-permissions';

interface NavItem {
  name: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  description: string;
  permission?: Permission;
}

const navigation: NavItem[] = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard, description: 'Overview & stats' },
  { name: 'Campaigns', href: '/campaigns', icon: Phone, description: 'Manage campaigns' },
  { name: 'Contacts', href: '/contacts', icon: Users, description: 'Contact lists' },
  { name: 'IVR Builder', href: '/ivr', icon: GitBranch, description: 'Voice flows', permission: 'ivr.access' },
  { name: 'Audio Files', href: '/audio', icon: Music, description: 'Voice prompts', permission: 'audio.access' },
  { name: 'Settings', href: '/settings', icon: Settings, description: 'Configuration', permission: 'settings.access' },
];

export function Sidebar() {
  const location = useLocation();
  const { user, logout } = useAuth();
  const { hasPermission, role } = usePermissions();

  // Filter navigation based on permissions
  const visibleNavigation = navigation.filter(
    (item) => !item.permission || hasPermission(item.permission)
  );

  return (
    <div className="flex h-full w-64 flex-col gradient-mesh border-r border-white/5">
      {/* Logo Section */}
      <div className="flex h-16 items-center gap-3 px-6 border-b border-white/5">
        <div className="w-9 h-9 rounded-lg gradient-primary flex items-center justify-center">
          <Phone className="w-5 h-5 text-white" />
        </div>
        <div>
          <h1 className="text-lg font-bold text-white">Auto-Dialer</h1>
          <p className="text-xs text-gray-500">Enterprise Edition</p>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        <p className="px-3 text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
          Main Menu
        </p>
        {visibleNavigation.map((item) => {
          const isActive = location.pathname === item.href ||
            (item.href !== '/' && location.pathname.startsWith(item.href));

          return (
            <NavLink
              key={item.name}
              to={item.href}
              className={cn(
                'group flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-200',
                isActive
                  ? 'bg-purple-500/20 text-white'
                  : 'text-gray-400 hover:bg-white/5 hover:text-white'
              )}
            >
              <div
                className={cn(
                  'flex items-center justify-center w-8 h-8 rounded-lg transition-colors',
                  isActive
                    ? 'bg-purple-500/30 text-purple-300'
                    : 'bg-white/5 text-gray-400 group-hover:bg-white/10 group-hover:text-white'
                )}
              >
                <item.icon className="w-4 h-4" aria-hidden="true" />
              </div>
              <div className="flex-1">
                <span className={cn(isActive && 'text-white')}>{item.name}</span>
              </div>
              <ChevronRight
                className={cn(
                  'w-4 h-4 opacity-0 -translate-x-2 transition-all',
                  'group-hover:opacity-100 group-hover:translate-x-0',
                  isActive && 'opacity-100 translate-x-0 text-purple-400'
                )}
              />
            </NavLink>
          );
        })}
      </nav>

      {/* User Section */}
      <div className="border-t border-white/5 p-4">
        <div className="flex items-center gap-3 px-2 py-2 rounded-lg bg-white/5">
          <div className="w-9 h-9 rounded-full bg-purple-500/20 flex items-center justify-center">
            <span className="text-sm font-semibold text-purple-300">
              {user?.first_name?.[0]?.toUpperCase() || user?.email?.[0]?.toUpperCase() || 'U'}
            </span>
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <p className="text-sm font-medium text-white truncate">
                {user?.first_name || 'User'}
              </p>
              {role && (
                <span className="text-xs px-1.5 py-0.5 rounded-full bg-purple-500/20 text-purple-300 capitalize">
                  {role}
                </span>
              )}
            </div>
            <p className="text-xs text-gray-500 truncate">
              {user?.email || 'user@example.com'}
            </p>
          </div>
          <button
            onClick={() => logout()}
            className="p-2 rounded-lg text-gray-400 hover:text-white hover:bg-white/10 transition-colors"
            title="Sign out"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>

        <p className="text-xs text-gray-600 text-center mt-4">
          v1.0.0 • SIP Auto-Dialer
        </p>
      </div>
    </div>
  );
}
