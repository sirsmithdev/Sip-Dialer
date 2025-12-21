import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Switch } from '@/components/ui/switch';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Info, Mail, CheckCircle, XCircle } from 'lucide-react';
import { usePermissions } from '@/hooks/use-permissions';
import { emailSettingsApi } from '@/services/api';
import type { EmailSettings, EmailSettingsCreate } from '@/types';

export function EmailSettingsForm() {
  const queryClient = useQueryClient();
  const { hasPermission } = usePermissions();
  const [isEditing, setIsEditing] = useState(false);
  const [testEmail, setTestEmail] = useState('');

  // Permission check for editing
  const canEdit = hasPermission('settings.edit');

  // Fetch existing settings
  const { data: settings, isLoading, error } = useQuery({
    queryKey: ['emailSettings'],
    queryFn: emailSettingsApi.get,
    retry: false,
  });

  // Form state
  const [formData, setFormData] = useState<Partial<EmailSettingsCreate>>({
    smtp_host: '',
    smtp_port: 587,
    smtp_username: '',
    smtp_password: '',
    from_email: '',
    from_name: 'SIP Auto-Dialer',
    use_tls: true,
    use_ssl: false,
  });

  // Initialize form with existing settings
  const initializeForm = (data: EmailSettings) => {
    setFormData({
      smtp_host: data.smtp_host,
      smtp_port: data.smtp_port,
      smtp_username: data.smtp_username,
      smtp_password: '', // Don't populate password
      from_email: data.from_email,
      from_name: data.from_name,
      use_tls: data.use_tls,
      use_ssl: data.use_ssl,
    });
  };

  // Create mutation
  const createMutation = useMutation({
    mutationFn: (data: EmailSettingsCreate) => emailSettingsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['emailSettings'] });
      setIsEditing(false);
    },
  });

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: (data: Partial<EmailSettingsCreate> & { is_active?: boolean }) =>
      emailSettingsApi.update(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['emailSettings'] });
      setIsEditing(false);
    },
  });

  // Test connection mutation
  const testConnectionMutation = useMutation({
    mutationFn: () => emailSettingsApi.testConnection(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['emailSettings'] });
    },
  });

  // Send test email mutation
  const sendTestEmailMutation = useMutation({
    mutationFn: (email: string) => emailSettingsApi.sendTestEmail({ to_email: email }),
  });

  // Toggle active status
  const toggleActiveMutation = useMutation({
    mutationFn: (isActive: boolean) => emailSettingsApi.update({ is_active: isActive }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['emailSettings'] });
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    // Remove empty password field if updating
    const submitData = { ...formData };
    if (!submitData.smtp_password) {
      delete submitData.smtp_password;
    }

    if (settings) {
      updateMutation.mutate(submitData);
    } else {
      createMutation.mutate(submitData as EmailSettingsCreate);
    }
  };

  const handleChange = (field: keyof EmailSettingsCreate, value: unknown) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const handleSendTestEmail = () => {
    if (testEmail) {
      sendTestEmailMutation.mutate(testEmail);
    }
  };

  if (isLoading) {
    return <div>Loading...</div>;
  }

  const hasSettings = !!settings && !error;

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Mail className="h-5 w-5" />
                Email Settings
              </CardTitle>
              <CardDescription>
                Configure SMTP settings for sending email reports and notifications
              </CardDescription>
            </div>
            {hasSettings && (
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-2">
                  <Switch
                    id="email-active"
                    checked={settings.is_active}
                    onCheckedChange={(checked) => toggleActiveMutation.mutate(checked)}
                    disabled={!canEdit}
                  />
                  <Label htmlFor="email-active">
                    {settings.is_active ? 'Enabled' : 'Disabled'}
                  </Label>
                </div>
                <Badge variant={settings.is_active ? 'default' : 'secondary'}>
                  {settings.is_active ? 'Active' : 'Inactive'}
                </Badge>
              </div>
            )}
          </div>
        </CardHeader>
        <CardContent>
          {!isEditing && hasSettings ? (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label className="text-muted-foreground">SMTP Server</Label>
                  <p className="font-medium">{settings.smtp_host}:{settings.smtp_port}</p>
                </div>
                <div>
                  <Label className="text-muted-foreground">Security</Label>
                  <p className="font-medium">
                    {settings.use_ssl ? 'SSL/TLS' : settings.use_tls ? 'STARTTLS' : 'None'}
                  </p>
                </div>
                <div>
                  <Label className="text-muted-foreground">Username</Label>
                  <p className="font-medium">{settings.smtp_username}</p>
                </div>
                <div>
                  <Label className="text-muted-foreground">From</Label>
                  <p className="font-medium">{settings.from_name} &lt;{settings.from_email}&gt;</p>
                </div>
              </div>

              {/* Last Test Status */}
              {settings.last_test_at && (
                <div className="pt-4 border-t">
                  <Label className="text-muted-foreground">Last Connection Test</Label>
                  <div className="flex items-center gap-2 mt-1">
                    {settings.last_test_success ? (
                      <CheckCircle className="h-4 w-4 text-green-600" />
                    ) : (
                      <XCircle className="h-4 w-4 text-red-600" />
                    )}
                    <span className={settings.last_test_success ? 'text-green-600' : 'text-red-600'}>
                      {settings.last_test_success ? 'Successful' : 'Failed'}
                    </span>
                    <span className="text-muted-foreground text-sm">
                      ({new Date(settings.last_test_at).toLocaleString()})
                    </span>
                  </div>
                  {settings.last_test_error && (
                    <p className="text-sm text-red-600 mt-1">{settings.last_test_error}</p>
                  )}
                </div>
              )}

              {canEdit ? (
                <Button onClick={() => { initializeForm(settings); setIsEditing(true); }}>
                  Edit Settings
                </Button>
              ) : (
                <Alert className="mt-4">
                  <Info className="h-4 w-4" />
                  <AlertDescription>
                    You have view-only access to settings. Contact an administrator to make changes.
                  </AlertDescription>
                </Alert>
              )}
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-6">
              {/* SMTP Server Settings */}
              <div className="space-y-4">
                <h3 className="font-semibold">SMTP Server</h3>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="smtp_host">SMTP Host</Label>
                    <Input
                      id="smtp_host"
                      placeholder="smtp.gmail.com"
                      value={formData.smtp_host}
                      onChange={(e) => handleChange('smtp_host', e.target.value)}
                      required
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="smtp_port">SMTP Port</Label>
                    <Input
                      id="smtp_port"
                      type="number"
                      placeholder="587"
                      value={formData.smtp_port}
                      onChange={(e) => handleChange('smtp_port', parseInt(e.target.value))}
                      required
                    />
                    <p className="text-xs text-muted-foreground">
                      587 for STARTTLS, 465 for SSL
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="smtp_username">Username</Label>
                    <Input
                      id="smtp_username"
                      placeholder="your-email@gmail.com"
                      value={formData.smtp_username}
                      onChange={(e) => handleChange('smtp_username', e.target.value)}
                      required
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="smtp_password">Password / App Password</Label>
                    <Input
                      id="smtp_password"
                      type="password"
                      placeholder={settings ? '(unchanged)' : 'App password for Gmail'}
                      value={formData.smtp_password}
                      onChange={(e) => handleChange('smtp_password', e.target.value)}
                      required={!settings}
                    />
                  </div>
                </div>
              </div>

              {/* Security Settings */}
              <div className="space-y-4">
                <h3 className="font-semibold">Security</h3>
                <div className="flex items-center gap-6">
                  <div className="flex items-center space-x-4">
                    <Switch
                      id="use_tls"
                      checked={formData.use_tls && !formData.use_ssl}
                      onCheckedChange={(checked) => {
                        handleChange('use_tls', checked);
                        if (checked) handleChange('use_ssl', false);
                      }}
                    />
                    <Label htmlFor="use_tls">Use STARTTLS (Port 587)</Label>
                  </div>
                  <div className="flex items-center space-x-4">
                    <Switch
                      id="use_ssl"
                      checked={formData.use_ssl}
                      onCheckedChange={(checked) => {
                        handleChange('use_ssl', checked);
                        if (checked) handleChange('use_tls', false);
                      }}
                    />
                    <Label htmlFor="use_ssl">Use SSL/TLS (Port 465)</Label>
                  </div>
                </div>
              </div>

              {/* Sender Settings */}
              <div className="space-y-4">
                <h3 className="font-semibold">Sender Information</h3>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="from_email">From Email</Label>
                    <Input
                      id="from_email"
                      type="email"
                      placeholder="reports@yourcompany.com"
                      value={formData.from_email}
                      onChange={(e) => handleChange('from_email', e.target.value)}
                      required
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="from_name">From Name</Label>
                    <Input
                      id="from_name"
                      placeholder="SIP Auto-Dialer"
                      value={formData.from_name}
                      onChange={(e) => handleChange('from_name', e.target.value)}
                    />
                  </div>
                </div>
              </div>

              {/* Gmail Note */}
              <Alert>
                <Info className="h-4 w-4" />
                <AlertDescription>
                  <strong>Gmail users:</strong> You'll need to use an App Password instead of your
                  regular password. Go to your Google Account &gt; Security &gt; 2-Step Verification
                  &gt; App Passwords to generate one.
                </AlertDescription>
              </Alert>

              {/* Form Actions */}
              <div className="flex space-x-4">
                <Button
                  type="submit"
                  disabled={createMutation.isPending || updateMutation.isPending}
                >
                  {createMutation.isPending || updateMutation.isPending
                    ? 'Saving...'
                    : settings
                    ? 'Update Settings'
                    : 'Save Settings'}
                </Button>
                {hasSettings && (
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => setIsEditing(false)}
                  >
                    Cancel
                  </Button>
                )}
              </div>

              {(createMutation.error || updateMutation.error) && (
                <p className="text-sm text-red-600">
                  Failed to save settings. Please try again.
                </p>
              )}
            </form>
          )}
        </CardContent>
      </Card>

      {/* Connection Test */}
      {hasSettings && (
        <Card>
          <CardHeader>
            <CardTitle>Connection Test</CardTitle>
            <CardDescription>
              Test SMTP connection and send a test email
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex gap-4">
              <Button
                variant="outline"
                onClick={() => testConnectionMutation.mutate()}
                disabled={testConnectionMutation.isPending}
              >
                {testConnectionMutation.isPending ? 'Testing...' : 'Test Connection'}
              </Button>

              {testConnectionMutation.data && (
                <div className={`flex items-center gap-2 ${
                  testConnectionMutation.data.success ? 'text-green-600' : 'text-red-600'
                }`}>
                  {testConnectionMutation.data.success ? (
                    <CheckCircle className="h-4 w-4" />
                  ) : (
                    <XCircle className="h-4 w-4" />
                  )}
                  <span>{testConnectionMutation.data.message}</span>
                </div>
              )}
            </div>

            <div className="pt-4 border-t">
              <Label htmlFor="test_email">Send Test Email</Label>
              <div className="flex gap-2 mt-2">
                <Input
                  id="test_email"
                  type="email"
                  placeholder="recipient@example.com"
                  value={testEmail}
                  onChange={(e) => setTestEmail(e.target.value)}
                  className="max-w-xs"
                />
                <Button
                  variant="outline"
                  onClick={handleSendTestEmail}
                  disabled={!testEmail || sendTestEmailMutation.isPending}
                >
                  {sendTestEmailMutation.isPending ? 'Sending...' : 'Send Test'}
                </Button>
              </div>

              {sendTestEmailMutation.data && (
                <div className={`mt-2 flex items-center gap-2 ${
                  sendTestEmailMutation.data.success ? 'text-green-600' : 'text-red-600'
                }`}>
                  {sendTestEmailMutation.data.success ? (
                    <CheckCircle className="h-4 w-4" />
                  ) : (
                    <XCircle className="h-4 w-4" />
                  )}
                  <span>{sendTestEmailMutation.data.message}</span>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
