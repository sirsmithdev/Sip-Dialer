import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { SipSettingsForm } from '@/components/settings/SipSettingsForm';
import { EmailSettingsForm } from '@/components/settings/EmailSettingsForm';
import { GeneralSettingsTab } from '@/components/settings/GeneralSettingsTab';
import { TestCallSettings } from '@/components/settings/TestCallSettings';
import { UserManagement } from '@/components/settings/UserManagement';
import { usePermissions } from '@/hooks/use-permissions';
import { Users } from 'lucide-react';

export function SettingsPage() {
  const { isSuperuser, hasRole } = usePermissions();
  const canManageUsers = isSuperuser || hasRole('admin');

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Settings</h1>
        <p className="text-muted-foreground">
          Configure your SIP Auto-Dialer application
        </p>
      </div>

      <Tabs defaultValue="sip" className="space-y-4">
        <TabsList>
          <TabsTrigger value="sip">SIP Configuration</TabsTrigger>
          <TabsTrigger value="test">Test Call</TabsTrigger>
          <TabsTrigger value="email">Email</TabsTrigger>
          {canManageUsers && (
            <TabsTrigger value="users" className="flex items-center gap-1">
              <Users className="w-4 h-4" />
              Users
            </TabsTrigger>
          )}
          <TabsTrigger value="general">General</TabsTrigger>
        </TabsList>

        <TabsContent value="sip">
          <SipSettingsForm />
        </TabsContent>

        <TabsContent value="test">
          <TestCallSettings />
        </TabsContent>

        <TabsContent value="email">
          <EmailSettingsForm />
        </TabsContent>

        {canManageUsers && (
          <TabsContent value="users">
            <UserManagement />
          </TabsContent>
        )}

        <TabsContent value="general">
          <GeneralSettingsTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}
