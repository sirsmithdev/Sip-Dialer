import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '@/hooks/use-auth';
import { usePermissions, Permission, UserRole } from '@/hooks/use-permissions';

interface ProtectedRouteProps {
  children: React.ReactNode;
  /** Single permission required to access this route */
  permission?: Permission;
  /** Multiple permissions - user needs ANY of these to access */
  permissions?: Permission[];
  /** Multiple roles - user needs ANY of these to access */
  roles?: UserRole[];
  /** Where to redirect if permission denied (default: /) */
  redirectTo?: string;
}

export function ProtectedRoute({
  children,
  permission,
  permissions,
  roles,
  redirectTo = '/',
}: ProtectedRouteProps) {
  const { isAuthenticated, isLoading } = useAuth();
  const { hasPermission, hasAnyPermission, hasRole } = usePermissions();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // Check single permission
  if (permission && !hasPermission(permission)) {
    return <Navigate to={redirectTo} replace />;
  }

  // Check multiple permissions (any)
  if (permissions && permissions.length > 0 && !hasAnyPermission(...permissions)) {
    return <Navigate to={redirectTo} replace />;
  }

  // Check roles (any)
  if (roles && roles.length > 0 && !hasRole(...roles)) {
    return <Navigate to={redirectTo} replace />;
  }

  return <>{children}</>;
}
