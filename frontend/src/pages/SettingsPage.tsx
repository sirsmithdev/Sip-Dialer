import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { SipSettingsForm } from '@/components/settings/SipSettingsForm';
import { EmailSettingsForm } from '@/components/settings/EmailSettingsForm';
import { GeneralSettingsTab } from '@/components/settings/GeneralSettingsTab';
import { TestCallSettings } from '@/components/settings/TestCallSettings';

export function SettingsPage() {
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

        <TabsContent value="general">
          <GeneralSettingsTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}
