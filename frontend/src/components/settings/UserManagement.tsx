import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Switch } from '@/components/ui/switch';
import { usersApi } from '@/services/api';
import { useAuth } from '@/hooks/use-auth';
import { usePermissions, Permission, UserRole } from '@/hooks/use-permissions';
import type { User } from '@/types';
import {
  Plus,
  Pencil,
  Trash2,
  Shield,
  ShieldCheck,
  ShieldAlert,
  UserCircle,
  Mail,
  Calendar,
  CheckCircle2,
  XCircle,
  Loader2,
  AlertTriangle,
  Eye,
  Users,
  Settings,
  Phone,
  Music,
  ListTree,
  Upload,
} from 'lucide-react';

// Permission groups for display
const PERMISSION_GROUPS = [
  {
    name: 'Campaigns',
    icon: Phone,
    permissions: [
      { key: 'campaigns.create', label: 'Create campaigns', description: 'Create new calling campaigns' },
      { key: 'campaigns.edit', label: 'Edit campaigns', description: 'Modify campaign settings' },
      { key: 'campaigns.delete', label: 'Delete campaigns', description: 'Remove campaigns permanently' },
      { key: 'campaigns.control', label: 'Control campaigns', description: 'Start, pause, resume, and cancel campaigns' },
    ],
  },
  {
    name: 'Contacts',
    icon: Users,
    permissions: [
      { key: 'contacts.import', label: 'Import contacts', description: 'Upload contact lists from files' },
      { key: 'contacts.delete', label: 'Delete contacts', description: 'Remove contact lists' },
    ],
  },
  {
    name: 'IVR & Audio',
    icon: ListTree,
    permissions: [
      { key: 'ivr.access', label: 'Access IVR builder', description: 'View and create IVR flows' },
      { key: 'audio.access', label: 'Access audio files', description: 'View uploaded audio files' },
      { key: 'audio.upload', label: 'Upload audio', description: 'Upload new audio files' },
      { key: 'audio.delete', label: 'Delete audio', description: 'Remove audio files' },
    ],
  },
  {
    name: 'Settings',
    icon: Settings,
    permissions: [
      { key: 'settings.access', label: 'Access settings', description: 'View system settings' },
      { key: 'settings.edit', label: 'Edit settings', description: 'Modify SIP, email, and other settings' },
    ],
  },
];

// Role to permissions mapping (same as in use-permissions.ts)
const ROLE_PERMISSIONS: Record<UserRole, Permission[]> = {
  admin: [
    'campaigns.create', 'campaigns.edit', 'campaigns.delete', 'campaigns.control',
    'contacts.import', 'contacts.delete',
    'ivr.access', 'audio.access', 'audio.upload', 'audio.delete',
    'settings.access', 'settings.edit',
  ],
  manager: [
    'campaigns.create', 'campaigns.edit', 'campaigns.control',
    'contacts.import',
    'ivr.access', 'audio.access', 'audio.upload',
    'settings.access',
  ],
  operator: [],
  viewer: [],
};

const ROLE_LABELS: Record<UserRole, { label: string; description: string; color: string }> = {
  admin: {
    label: 'Administrator',
    description: 'Full system access with all permissions',
    color: 'bg-red-500',
  },
  manager: {
    label: 'Manager',
    description: 'Can manage campaigns, contacts, and IVR flows',
    color: 'bg-blue-500',
  },
  operator: {
    label: 'Operator',
    description: 'View-only access to the system',
    color: 'bg-yellow-500',
  },
  viewer: {
    label: 'Viewer',
    description: 'View-only access with no modification rights',
    color: 'bg-gray-500',
  },
};

interface UserFormData {
  email: string;
  password: string;
  first_name: string;
  last_name: string;
  role: UserRole;
  is_active: boolean;
}

const initialFormData: UserFormData = {
  email: '',
  password: '',
  first_name: '',
  last_name: '',
  role: 'operator',
  is_active: true,
};

export function UserManagement() {
  const { user: currentUser } = useAuth();
  const { isSuperuser, hasRole } = usePermissions();
  const queryClient = useQueryClient();

  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [isPermissionsDialogOpen, setIsPermissionsDialogOpen] = useState(false);
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [formData, setFormData] = useState<UserFormData>(initialFormData);
  const [formError, setFormError] = useState<string | null>(null);

  // Check if current user can manage users (admin or superuser)
  const canManageUsers = isSuperuser || hasRole('admin');

  // Fetch users
  const { data: users, isLoading, error } = useQuery({
    queryKey: ['users'],
    queryFn: usersApi.list,
    enabled: canManageUsers,
  });

  // Create user mutation
  const createUserMutation = useMutation({
    mutationFn: (data: Partial<User> & { password: string }) => usersApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
      setIsCreateDialogOpen(false);
      setFormData(initialFormData);
      setFormError(null);
    },
    onError: (error: Error) => {
      setFormError(error.message || 'Failed to create user');
    },
  });

  // Update user mutation
  const updateUserMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<User> }) => usersApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
      setIsEditDialogOpen(false);
      setSelectedUser(null);
      setFormData(initialFormData);
      setFormError(null);
    },
    onError: (error: Error) => {
      setFormError(error.message || 'Failed to update user');
    },
  });

  // Delete user mutation
  const deleteUserMutation = useMutation({
    mutationFn: (id: string) => usersApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
      setIsDeleteDialogOpen(false);
      setSelectedUser(null);
    },
  });

  const handleCreateUser = () => {
    setFormError(null);
    if (!formData.email || !formData.password) {
      setFormError('Email and password are required');
      return;
    }
    createUserMutation.mutate({
      email: formData.email,
      password: formData.password,
      first_name: formData.first_name || null,
      last_name: formData.last_name || null,
      role: formData.role,
      is_active: formData.is_active,
    });
  };

  const handleUpdateUser = () => {
    if (!selectedUser) return;
    setFormError(null);

    const updateData: Partial<User> = {
      first_name: formData.first_name || null,
      last_name: formData.last_name || null,
      role: formData.role,
      is_active: formData.is_active,
    };

    // Only include email if changed
    if (formData.email !== selectedUser.email) {
      updateData.email = formData.email;
    }

    updateUserMutation.mutate({ id: selectedUser.id, data: updateData });
  };

  const openEditDialog = (user: User) => {
    setSelectedUser(user);
    setFormData({
      email: user.email,
      password: '',
      first_name: user.first_name || '',
      last_name: user.last_name || '',
      role: user.role,
      is_active: user.is_active,
    });
    setFormError(null);
    setIsEditDialogOpen(true);
  };

  const openDeleteDialog = (user: User) => {
    setSelectedUser(user);
    setIsDeleteDialogOpen(true);
  };

  const openPermissionsDialog = (user: User) => {
    setSelectedUser(user);
    setIsPermissionsDialogOpen(true);
  };

  const getRoleBadgeColor = (role: UserRole) => {
    switch (role) {
      case 'admin':
        return 'bg-red-500/10 text-red-600 border-red-200';
      case 'manager':
        return 'bg-blue-500/10 text-blue-600 border-blue-200';
      case 'operator':
        return 'bg-yellow-500/10 text-yellow-600 border-yellow-200';
      case 'viewer':
        return 'bg-gray-500/10 text-gray-600 border-gray-200';
      default:
        return 'bg-gray-500/10 text-gray-600 border-gray-200';
    }
  };

  if (!canManageUsers) {
    return (
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <ShieldAlert className="w-12 h-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold mb-2">Access Denied</h3>
            <p className="text-muted-foreground max-w-sm">
              You don't have permission to manage users. Contact an administrator for access.
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (isLoading) {
    return (
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <AlertTriangle className="w-12 h-12 text-destructive mb-4" />
            <h3 className="text-lg font-semibold mb-2">Error Loading Users</h3>
            <p className="text-muted-foreground">
              {error instanceof Error ? error.message : 'Unknown error occurred'}
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Users className="w-5 h-5" />
                User Management
              </CardTitle>
              <CardDescription>
                Add, edit, and manage user accounts and their permissions
              </CardDescription>
            </div>
            <Button onClick={() => {
              setFormData(initialFormData);
              setFormError(null);
              setIsCreateDialogOpen(true);
            }}>
              <Plus className="w-4 h-4 mr-2" />
              Add User
            </Button>
          </div>
        </CardHeader>
      </Card>

      {/* Users List */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Users ({users?.length || 0})</CardTitle>
        </CardHeader>
        <CardContent>
          {users && users.length > 0 ? (
            <div className="space-y-4">
              {users.map((user) => (
                <div
                  key={user.id}
                  className="flex items-center justify-between p-4 border rounded-lg hover:bg-muted/50 transition-colors"
                >
                  <div className="flex items-center gap-4">
                    <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
                      <UserCircle className="w-6 h-6 text-primary" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-medium">
                          {user.first_name && user.last_name
                            ? `${user.first_name} ${user.last_name}`
                            : user.email}
                        </span>
                        {user.is_superuser && (
                          <Badge variant="outline" className="bg-purple-500/10 text-purple-600 border-purple-200">
                            <ShieldCheck className="w-3 h-3 mr-1" />
                            Superuser
                          </Badge>
                        )}
                        <Badge variant="outline" className={getRoleBadgeColor(user.role)}>
                          {ROLE_LABELS[user.role]?.label || user.role}
                        </Badge>
                        {!user.is_active && (
                          <Badge variant="outline" className="bg-red-500/10 text-red-600 border-red-200">
                            Inactive
                          </Badge>
                        )}
                      </div>
                      <div className="flex items-center gap-4 text-sm text-muted-foreground mt-1">
                        <span className="flex items-center gap-1">
                          <Mail className="w-3 h-3" />
                          {user.email}
                        </span>
                        {user.last_login && (
                          <span className="flex items-center gap-1">
                            <Calendar className="w-3 h-3" />
                            Last login: {new Date(user.last_login).toLocaleDateString()}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => openPermissionsDialog(user)}
                      title="View permissions"
                    >
                      <Eye className="w-4 h-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => openEditDialog(user)}
                      disabled={user.id === currentUser?.id && !isSuperuser}
                      title="Edit user"
                    >
                      <Pencil className="w-4 h-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => openDeleteDialog(user)}
                      disabled={user.id === currentUser?.id}
                      className="text-destructive hover:text-destructive"
                      title="Delete user"
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <Users className="w-12 h-12 text-muted-foreground mb-4" />
              <h3 className="text-lg font-semibold mb-2">No Users Found</h3>
              <p className="text-muted-foreground mb-4">
                Get started by adding your first user.
              </p>
              <Button onClick={() => setIsCreateDialogOpen(true)}>
                <Plus className="w-4 h-4 mr-2" />
                Add User
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Role Permissions Reference */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <Shield className="w-5 h-5" />
            Role Permissions Reference
          </CardTitle>
          <CardDescription>
            Understanding what each role can do in the system
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-2">
            {(Object.keys(ROLE_LABELS) as UserRole[]).map((role) => (
              <div key={role} className="p-4 border rounded-lg">
                <div className="flex items-center gap-2 mb-2">
                  <div className={`w-3 h-3 rounded-full ${ROLE_LABELS[role].color}`} />
                  <span className="font-medium">{ROLE_LABELS[role].label}</span>
                </div>
                <p className="text-sm text-muted-foreground mb-3">
                  {ROLE_LABELS[role].description}
                </p>
                <div className="text-xs text-muted-foreground">
                  {ROLE_PERMISSIONS[role].length > 0 ? (
                    <span>{ROLE_PERMISSIONS[role].length} permissions</span>
                  ) : (
                    <span>View-only access</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Create User Dialog */}
      <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>Add New User</DialogTitle>
            <DialogDescription>
              Create a new user account with the specified role and permissions.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            {formError && (
              <div className="p-3 bg-destructive/10 text-destructive rounded-md text-sm">
                {formError}
              </div>
            )}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="first_name">First Name</Label>
                <Input
                  id="first_name"
                  value={formData.first_name}
                  onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
                  placeholder="John"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="last_name">Last Name</Label>
                <Input
                  id="last_name"
                  value={formData.last_name}
                  onChange={(e) => setFormData({ ...formData, last_name: e.target.value })}
                  placeholder="Doe"
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="email">Email *</Label>
              <Input
                id="email"
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                placeholder="john@example.com"
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Password *</Label>
              <Input
                id="password"
                type="password"
                value={formData.password}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                placeholder="Enter a secure password"
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="role">Role</Label>
              <Select
                value={formData.role}
                onValueChange={(value: UserRole) => setFormData({ ...formData, role: value })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select a role" />
                </SelectTrigger>
                <SelectContent>
                  {(Object.keys(ROLE_LABELS) as UserRole[]).map((role) => (
                    <SelectItem key={role} value={role}>
                      <div className="flex items-center gap-2">
                        <div className={`w-2 h-2 rounded-full ${ROLE_LABELS[role].color}`} />
                        {ROLE_LABELS[role].label}
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                {ROLE_LABELS[formData.role]?.description}
              </p>
            </div>
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label htmlFor="is_active">Active Status</Label>
                <p className="text-xs text-muted-foreground">
                  Inactive users cannot log in
                </p>
              </div>
              <Switch
                id="is_active"
                checked={formData.is_active}
                onCheckedChange={(checked) => setFormData({ ...formData, is_active: checked })}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsCreateDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleCreateUser} disabled={createUserMutation.isPending}>
              {createUserMutation.isPending && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
              Create User
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit User Dialog */}
      <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>Edit User</DialogTitle>
            <DialogDescription>
              Update user details and role assignment.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            {formError && (
              <div className="p-3 bg-destructive/10 text-destructive rounded-md text-sm">
                {formError}
              </div>
            )}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="edit_first_name">First Name</Label>
                <Input
                  id="edit_first_name"
                  value={formData.first_name}
                  onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
                  placeholder="John"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="edit_last_name">Last Name</Label>
                <Input
                  id="edit_last_name"
                  value={formData.last_name}
                  onChange={(e) => setFormData({ ...formData, last_name: e.target.value })}
                  placeholder="Doe"
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit_email">Email</Label>
              <Input
                id="edit_email"
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                placeholder="john@example.com"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit_role">Role</Label>
              <Select
                value={formData.role}
                onValueChange={(value: UserRole) => setFormData({ ...formData, role: value })}
                disabled={selectedUser?.id === currentUser?.id}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select a role" />
                </SelectTrigger>
                <SelectContent>
                  {(Object.keys(ROLE_LABELS) as UserRole[]).map((role) => (
                    <SelectItem key={role} value={role}>
                      <div className="flex items-center gap-2">
                        <div className={`w-2 h-2 rounded-full ${ROLE_LABELS[role].color}`} />
                        {ROLE_LABELS[role].label}
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {selectedUser?.id === currentUser?.id && (
                <p className="text-xs text-muted-foreground">
                  You cannot change your own role
                </p>
              )}
            </div>
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label htmlFor="edit_is_active">Active Status</Label>
                <p className="text-xs text-muted-foreground">
                  Inactive users cannot log in
                </p>
              </div>
              <Switch
                id="edit_is_active"
                checked={formData.is_active}
                onCheckedChange={(checked) => setFormData({ ...formData, is_active: checked })}
                disabled={selectedUser?.id === currentUser?.id}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsEditDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleUpdateUser} disabled={updateUserMutation.isPending}>
              {updateUserMutation.isPending && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
              Save Changes
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete User Confirmation */}
      <AlertDialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete User</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete{' '}
              <span className="font-medium">
                {selectedUser?.first_name
                  ? `${selectedUser.first_name} ${selectedUser.last_name || ''}`
                  : selectedUser?.email}
              </span>
              ? This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => selectedUser && deleteUserMutation.mutate(selectedUser.id)}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {deleteUserMutation.isPending && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* View Permissions Dialog */}
      <Dialog open={isPermissionsDialogOpen} onOpenChange={setIsPermissionsDialogOpen}>
        <DialogContent className="sm:max-w-[600px] max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Shield className="w-5 h-5" />
              User Permissions
            </DialogTitle>
            <DialogDescription>
              Permissions for{' '}
              <span className="font-medium">
                {selectedUser?.first_name
                  ? `${selectedUser.first_name} ${selectedUser.last_name || ''}`
                  : selectedUser?.email}
              </span>
              {selectedUser?.is_superuser && (
                <Badge variant="outline" className="ml-2 bg-purple-500/10 text-purple-600 border-purple-200">
                  Superuser - All Access
                </Badge>
              )}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-6 py-4">
            {/* Role Info */}
            <div className="p-4 bg-muted/50 rounded-lg">
              <div className="flex items-center gap-2 mb-2">
                <div className={`w-3 h-3 rounded-full ${ROLE_LABELS[selectedUser?.role || 'viewer'].color}`} />
                <span className="font-medium">{ROLE_LABELS[selectedUser?.role || 'viewer'].label}</span>
              </div>
              <p className="text-sm text-muted-foreground">
                {ROLE_LABELS[selectedUser?.role || 'viewer'].description}
              </p>
            </div>

            <Separator />

            {/* Permission Groups */}
            {PERMISSION_GROUPS.map((group) => {
              const GroupIcon = group.icon;
              const userPermissions = selectedUser?.is_superuser
                ? group.permissions.map((p) => p.key)
                : ROLE_PERMISSIONS[selectedUser?.role || 'viewer'];

              return (
                <div key={group.name} className="space-y-3">
                  <div className="flex items-center gap-2">
                    <GroupIcon className="w-4 h-4 text-muted-foreground" />
                    <h4 className="font-medium">{group.name}</h4>
                  </div>
                  <div className="grid gap-2 pl-6">
                    {group.permissions.map((permission) => {
                      const hasPermission = userPermissions.includes(permission.key as Permission);
                      return (
                        <div
                          key={permission.key}
                          className={`flex items-center justify-between p-2 rounded-md ${
                            hasPermission ? 'bg-green-500/10' : 'bg-muted/30'
                          }`}
                        >
                          <div>
                            <div className="flex items-center gap-2">
                              {hasPermission ? (
                                <CheckCircle2 className="w-4 h-4 text-green-600" />
                              ) : (
                                <XCircle className="w-4 h-4 text-muted-foreground" />
                              )}
                              <span className={hasPermission ? 'text-foreground' : 'text-muted-foreground'}>
                                {permission.label}
                              </span>
                            </div>
                            <p className="text-xs text-muted-foreground pl-6">
                              {permission.description}
                            </p>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>
          <DialogFooter>
            <Button onClick={() => setIsPermissionsDialogOpen(false)}>Close</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
