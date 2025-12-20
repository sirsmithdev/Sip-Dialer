import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Info } from 'lucide-react';
import { usePermissions } from '@/hooks/use-permissions';
import { sipSettingsApi } from '@/services/api';
import type { SIPSettings, SIPSettingsCreate } from '@/types';

const AVAILABLE_CODECS = [
  { value: 'ulaw', label: 'G.711 u-law' },
  { value: 'alaw', label: 'G.711 a-law' },
  { value: 'g722', label: 'G.722' },
  { value: 'g729', label: 'G.729' },
  { value: 'gsm', label: 'GSM' },
];

export function SipSettingsForm() {
  const queryClient = useQueryClient();
  const { hasPermission } = usePermissions();
  const [isEditing, setIsEditing] = useState(false);

  // Permission check for editing
  const canEdit = hasPermission('settings.edit');

  // Fetch existing settings
  const { data: settings, isLoading, error } = useQuery({
    queryKey: ['sipSettings'],
    queryFn: sipSettingsApi.get,
    retry: false,
  });

  // Form state
  const [formData, setFormData] = useState<Partial<SIPSettingsCreate>>({
    sip_server: '',
    sip_port: 5060,
    sip_username: '',
    sip_password: '',
    sip_transport: 'UDP',
    registration_required: true,
    register_expires: 3600,
    keepalive_enabled: true,
    keepalive_interval: 30,
    rtp_port_start: 10000,
    rtp_port_end: 20000,
    codecs: ['ulaw', 'alaw', 'g722'],
    default_caller_id: '',
    caller_id_name: '',
  });

  // Initialize form with existing settings
  const initializeForm = (data: SIPSettings) => {
    setFormData({
      sip_server: data.sip_server,
      sip_port: data.sip_port,
      sip_username: data.sip_username,
      sip_password: '', // Don't populate password
      sip_transport: data.sip_transport,
      registration_required: data.registration_required,
      register_expires: data.register_expires,
      keepalive_enabled: data.keepalive_enabled,
      keepalive_interval: data.keepalive_interval,
      rtp_port_start: data.rtp_port_start,
      rtp_port_end: data.rtp_port_end,
      codecs: data.codecs,
      default_caller_id: data.default_caller_id || '',
      caller_id_name: data.caller_id_name || '',
    });
  };

  // Create mutation
  const createMutation = useMutation({
    mutationFn: (data: SIPSettingsCreate) => sipSettingsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sipSettings'] });
      setIsEditing(false);
    },
  });

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: (data: Partial<SIPSettingsCreate>) => sipSettingsApi.update(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sipSettings'] });
      setIsEditing(false);
    },
  });

  // Test connection mutation
  const testMutation = useMutation({
    mutationFn: () => sipSettingsApi.testConnection(),
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    // Remove empty password field if updating
    const submitData = { ...formData };
    if (!submitData.sip_password) {
      delete submitData.sip_password;
    }

    if (settings) {
      updateMutation.mutate(submitData);
    } else {
      createMutation.mutate(submitData as SIPSettingsCreate);
    }
  };

  const handleChange = (field: keyof SIPSettingsCreate, value: unknown) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const handleCodecToggle = (codec: string) => {
    setFormData((prev) => {
      const codecs = prev.codecs || [];
      if (codecs.includes(codec)) {
        return { ...prev, codecs: codecs.filter((c) => c !== codec) };
      } else {
        return { ...prev, codecs: [...codecs, codec] };
      }
    });
  };

  if (isLoading) {
    return <div>Loading...</div>;
  }

  const hasSettings = !!settings && !error;

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>SIP Connection Settings</CardTitle>
          <CardDescription>
            Configure the connection to your Grandstream UCM6302 or other Asterisk-based PBX
          </CardDescription>
        </CardHeader>
        <CardContent>
          {!isEditing && hasSettings ? (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label className="text-muted-foreground">SIP Server</Label>
                  <p className="font-medium">{settings.sip_server}:{settings.sip_port}</p>
                </div>
                <div>
                  <Label className="text-muted-foreground">Transport</Label>
                  <p className="font-medium">{settings.sip_transport}</p>
                </div>
                <div>
                  <Label className="text-muted-foreground">Username</Label>
                  <p className="font-medium">{settings.sip_username}</p>
                </div>
                <div>
                  <Label className="text-muted-foreground">Status</Label>
                  <p className={`font-medium ${
                    settings.connection_status === 'connected' || settings.connection_status === 'registered'
                      ? 'text-green-600'
                      : settings.connection_status === 'failed'
                      ? 'text-red-600'
                      : 'text-yellow-600'
                  }`}>
                    {settings.connection_status}
                  </p>
                </div>
              </div>
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
              {/* SIP Server Settings */}
              <div className="space-y-4">
                <h3 className="font-semibold">SIP Server</h3>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="sip_server">Server Address</Label>
                    <Input
                      id="sip_server"
                      placeholder="192.168.1.100 or pbx.example.com"
                      value={formData.sip_server}
                      onChange={(e) => handleChange('sip_server', e.target.value)}
                      required
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="sip_port">SIP Port</Label>
                    <Input
                      id="sip_port"
                      type="number"
                      value={formData.sip_port}
                      onChange={(e) => handleChange('sip_port', parseInt(e.target.value))}
                      required
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="sip_username">SIP Username</Label>
                    <Input
                      id="sip_username"
                      placeholder="autodialer"
                      value={formData.sip_username}
                      onChange={(e) => handleChange('sip_username', e.target.value)}
                      required
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="sip_password">SIP Password</Label>
                    <Input
                      id="sip_password"
                      type="password"
                      placeholder={settings ? '(unchanged)' : ''}
                      value={formData.sip_password}
                      onChange={(e) => handleChange('sip_password', e.target.value)}
                      required={!settings}
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="sip_transport">Transport Protocol</Label>
                    <Select
                      value={formData.sip_transport}
                      onValueChange={(value) => handleChange('sip_transport', value)}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="UDP">UDP</SelectItem>
                        <SelectItem value="TCP">TCP</SelectItem>
                        <SelectItem value="TLS">TLS</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </div>

              {/* Registration Settings */}
              <div className="space-y-4">
                <h3 className="font-semibold">Registration</h3>
                <div className="flex items-center space-x-4">
                  <Switch
                    id="registration_required"
                    checked={formData.registration_required}
                    onCheckedChange={(checked) => handleChange('registration_required', checked)}
                  />
                  <Label htmlFor="registration_required">Registration Required</Label>
                </div>
                {formData.registration_required && (
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="register_expires">Registration Expiry (seconds)</Label>
                      <Input
                        id="register_expires"
                        type="number"
                        value={formData.register_expires}
                        onChange={(e) => handleChange('register_expires', parseInt(e.target.value))}
                      />
                    </div>
                  </div>
                )}
              </div>

              {/* Keep-Alive Settings */}
              <div className="space-y-4">
                <h3 className="font-semibold">Keep-Alive</h3>
                <div className="flex items-center space-x-4">
                  <Switch
                    id="keepalive_enabled"
                    checked={formData.keepalive_enabled}
                    onCheckedChange={(checked) => handleChange('keepalive_enabled', checked)}
                  />
                  <Label htmlFor="keepalive_enabled">Enable Keep-Alive</Label>
                </div>
                {formData.keepalive_enabled && (
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="keepalive_interval">Keep-Alive Interval (seconds)</Label>
                      <Input
                        id="keepalive_interval"
                        type="number"
                        value={formData.keepalive_interval}
                        onChange={(e) => handleChange('keepalive_interval', parseInt(e.target.value))}
                      />
                    </div>
                  </div>
                )}
              </div>

              {/* RTP Settings */}
              <div className="space-y-4">
                <h3 className="font-semibold">RTP/Media Ports</h3>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="rtp_port_start">RTP Port Start</Label>
                    <Input
                      id="rtp_port_start"
                      type="number"
                      value={formData.rtp_port_start}
                      onChange={(e) => handleChange('rtp_port_start', parseInt(e.target.value))}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="rtp_port_end">RTP Port End</Label>
                    <Input
                      id="rtp_port_end"
                      type="number"
                      value={formData.rtp_port_end}
                      onChange={(e) => handleChange('rtp_port_end', parseInt(e.target.value))}
                    />
                  </div>
                </div>
              </div>

              {/* Codec Settings */}
              <div className="space-y-4">
                <h3 className="font-semibold">Audio Codecs</h3>
                <p className="text-sm text-muted-foreground">Select codecs in order of preference</p>
                <div className="space-y-2">
                  {AVAILABLE_CODECS.map((codec) => (
                    <div key={codec.value} className="flex items-center space-x-4">
                      <Switch
                        id={`codec-${codec.value}`}
                        checked={formData.codecs?.includes(codec.value)}
                        onCheckedChange={() => handleCodecToggle(codec.value)}
                      />
                      <Label htmlFor={`codec-${codec.value}`}>{codec.label}</Label>
                    </div>
                  ))}
                </div>
              </div>

              {/* Caller ID Settings */}
              <div className="space-y-4">
                <h3 className="font-semibold">Caller ID</h3>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="default_caller_id">Default Caller ID Number</Label>
                    <Input
                      id="default_caller_id"
                      placeholder="+15551234567"
                      value={formData.default_caller_id}
                      onChange={(e) => handleChange('default_caller_id', e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="caller_id_name">Caller ID Name</Label>
                    <Input
                      id="caller_id_name"
                      placeholder="Auto Dialer"
                      value={formData.caller_id_name}
                      onChange={(e) => handleChange('caller_id_name', e.target.value)}
                    />
                  </div>
                </div>
              </div>

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
              Test connectivity to your PJSIP server
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button
              variant="outline"
              onClick={() => testMutation.mutate()}
              disabled={testMutation.isPending}
            >
              {testMutation.isPending ? 'Testing...' : 'Test SIP Connection'}
            </Button>
            {testMutation.data && (
              <div className={`mt-4 p-4 rounded-md ${
                testMutation.data.success ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'
              }`}>
                <p className="font-medium">{testMutation.data.success ? 'Success' : 'Failed'}</p>
                <p className="text-sm">{testMutation.data.message}</p>
                {testMutation.data.test_steps && testMutation.data.test_steps.length > 0 && (
                  <div className="mt-2 text-xs font-mono">
                    {testMutation.data.test_steps.map((step, index) => (
                      <p key={index}>{step}</p>
                    ))}
                  </div>
                )}
                {testMutation.data.diagnostic_hint && (
                  <p className="mt-2 text-sm italic">{testMutation.data.diagnostic_hint}</p>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
