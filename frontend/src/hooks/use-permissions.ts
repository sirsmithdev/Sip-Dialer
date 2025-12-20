import { useAuth } from './use-auth';

// User roles matching backend UserRole enum
export type UserRole = 'admin' | 'manager' | 'operator' | 'viewer';

// Granular permissions for UI elements
export type Permission =
  | 'campaigns.create'
  | 'campaigns.edit'
  | 'campaigns.delete'
  | 'campaigns.control' // start, pause, resume, cancel
  | 'contacts.import'
  | 'contacts.delete'
  | 'ivr.access'
  | 'audio.access'
  | 'audio.upload'
  | 'audio.delete'
  | 'settings.access'
  | 'settings.edit';

// Role to permissions mapping
const ROLE_PERMISSIONS: Record<UserRole, Permission[]> = {
  admin: [
    'campaigns.create',
    'campaigns.edit',
    'campaigns.delete',
    'campaigns.control',
    'contacts.import',
    'contacts.delete',
    'ivr.access',
    'audio.access',
    'audio.upload',
    'audio.delete',
    'settings.access',
    'settings.edit',
  ],
  manager: [
    'campaigns.create',
    'campaigns.edit',
    'campaigns.control',
    'contacts.import',
    'ivr.access',
    'audio.access',
    'audio.upload',
    'settings.access',
  ],
  operator: [],
  viewer: [],
};

export interface UsePermissionsReturn {
  /** Check if user has a specific permission */
  hasPermission: (permission: Permission) => boolean;
  /** Check if user has any of the given permissions */
  hasAnyPermission: (...permissions: Permission[]) => boolean;
  /** Check if user has all of the given permissions */
  hasAllPermissions: (...permissions: Permission[]) => boolean;
  /** Check if user has any of the given roles */
  hasRole: (...roles: UserRole[]) => boolean;
  /** Current user's role */
  role: UserRole | null;
  /** Whether user is a superuser (bypasses all checks) */
  isSuperuser: boolean;
}

export function usePermissions(): UsePermissionsReturn {
  const { user } = useAuth();

  const role = (user?.role as UserRole) || null;
  const isSuperuser = user?.is_superuser || false;

  const hasPermission = (permission: Permission): boolean => {
    // Superusers have all permissions
    if (isSuperuser) return true;

    // No role means no permissions
    if (!role) return false;

    // Check if role has the permission
    return ROLE_PERMISSIONS[role]?.includes(permission) || false;
  };

  const hasAnyPermission = (...permissions: Permission[]): boolean => {
    if (isSuperuser) return true;
    return permissions.some((p) => hasPermission(p));
  };

  const hasAllPermissions = (...permissions: Permission[]): boolean => {
    if (isSuperuser) return true;
    return permissions.every((p) => hasPermission(p));
  };

  const hasRole = (...roles: UserRole[]): boolean => {
    if (isSuperuser) return true;
    if (!role) return false;
    return roles.includes(role);
  };

  return {
    hasPermission,
    hasAnyPermission,
    hasAllPermissions,
    hasRole,
    role,
    isSuperuser,
  };
}
