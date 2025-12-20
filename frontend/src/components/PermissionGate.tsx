import { ReactNode } from 'react';
import { usePermissions, Permission, UserRole } from '@/hooks/use-permissions';

interface PermissionGateProps {
  /** Single permission to check */
  permission?: Permission;
  /** Multiple permissions - user needs ANY of these */
  permissions?: Permission[];
  /** Multiple roles - user needs ANY of these */
  roles?: UserRole[];
  /** Content to render if user has permission */
  children: ReactNode;
  /** Optional fallback content if user doesn't have permission */
  fallback?: ReactNode;
}

/**
 * Conditionally renders children based on user permissions.
 *
 * @example
 * // Single permission
 * <PermissionGate permission="campaigns.create">
 *   <Button>Create Campaign</Button>
 * </PermissionGate>
 *
 * @example
 * // Multiple permissions (any)
 * <PermissionGate permissions={['campaigns.create', 'campaigns.edit']}>
 *   <Button>Manage Campaign</Button>
 * </PermissionGate>
 *
 * @example
 * // Role-based
 * <PermissionGate roles={['admin', 'manager']}>
 *   <AdminPanel />
 * </PermissionGate>
 *
 * @example
 * // With fallback
 * <PermissionGate permission="settings.edit" fallback={<span>Read-only</span>}>
 *   <Button>Save</Button>
 * </PermissionGate>
 */
export function PermissionGate({
  permission,
  permissions,
  roles,
  children,
  fallback = null,
}: PermissionGateProps) {
  const { hasPermission, hasAnyPermission, hasRole } = usePermissions();

  // Check single permission
  if (permission && !hasPermission(permission)) {
    return <>{fallback}</>;
  }

  // Check multiple permissions (any)
  if (permissions && permissions.length > 0 && !hasAnyPermission(...permissions)) {
    return <>{fallback}</>;
  }

  // Check roles (any)
  if (roles && roles.length > 0 && !hasRole(...roles)) {
    return <>{fallback}</>;
  }

  return <>{children}</>;
}

/**
 * Hook-based alternative for more complex permission logic.
 * Use when you need to conditionally set props rather than hide elements.
 *
 * @example
 * const { canEdit } = usePermissionCheck({ permission: 'settings.edit' });
 * <Input disabled={!canEdit} />
 */
export function usePermissionCheck(options: {
  permission?: Permission;
  permissions?: Permission[];
  roles?: UserRole[];
}): { allowed: boolean } {
  const { hasPermission, hasAnyPermission, hasRole } = usePermissions();

  let allowed = true;

  if (options.permission) {
    allowed = allowed && hasPermission(options.permission);
  }

  if (options.permissions && options.permissions.length > 0) {
    allowed = allowed && hasAnyPermission(...options.permissions);
  }

  if (options.roles && options.roles.length > 0) {
    allowed = allowed && hasRole(...options.roles);
  }

  return { allowed };
}
