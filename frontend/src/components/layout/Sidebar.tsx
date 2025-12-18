import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Phone,
  Users,
  Music,
  Settings,
  GitBranch,
} from 'lucide-react';
import { cn } from '@/lib/utils';

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Campaigns', href: '/campaigns', icon: Phone },
  { name: 'Contacts', href: '/contacts', icon: Users },
  { name: 'IVR Builder', href: '/ivr', icon: GitBranch },
  { name: 'Audio Files', href: '/audio', icon: Music },
  { name: 'Settings', href: '/settings', icon: Settings },
];

export function Sidebar() {
  return (
    <div className="flex h-full w-64 flex-col bg-gray-900">
      <div className="flex h-16 items-center justify-center border-b border-gray-800">
        <h1 className="text-xl font-bold text-white">SIP Auto-Dialer</h1>
      </div>
      <nav className="flex-1 space-y-1 px-2 py-4">
        {navigation.map((item) => (
          <NavLink
            key={item.name}
            to={item.href}
            className={({ isActive }) =>
              cn(
                'group flex items-center rounded-md px-3 py-2 text-sm font-medium transition-colors',
                isActive
                  ? 'bg-gray-800 text-white'
                  : 'text-gray-300 hover:bg-gray-800 hover:text-white'
              )
            }
          >
            <item.icon
              className="mr-3 h-5 w-5 flex-shrink-0"
              aria-hidden="true"
            />
            {item.name}
          </NavLink>
        ))}
      </nav>
      <div className="border-t border-gray-800 p-4">
        <p className="text-xs text-gray-500 text-center">
          v1.0.0
        </p>
      </div>
    </div>
  );
}
