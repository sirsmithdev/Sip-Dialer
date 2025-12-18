import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { SipSettingsForm } from '@/components/settings/SipSettingsForm';
import { AudioSettingsTab } from '@/components/settings/AudioSettingsTab';
import { GeneralSettingsTab } from '@/components/settings/GeneralSettingsTab';

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
          <TabsTrigger value="audio">Audio</TabsTrigger>
          <TabsTrigger value="general">General</TabsTrigger>
        </TabsList>

        <TabsContent value="sip">
          <SipSettingsForm />
        </TabsContent>

        <TabsContent value="audio">
          <AudioSettingsTab />
        </TabsContent>

        <TabsContent value="general">
          <GeneralSettingsTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}
