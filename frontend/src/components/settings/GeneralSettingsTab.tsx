import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';

// General settings stored in localStorage
interface GeneralSettings {
  timezone: string;
  dateFormat: string;
  timeFormat: '12h' | '24h';
  pageSize: number;
  soundNotifications: boolean;
  emailNotifications: boolean;
  autoRefreshInterval: number;
}

const DEFAULT_SETTINGS: GeneralSettings = {
  timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC',
  dateFormat: 'MM/DD/YYYY',
  timeFormat: '12h',
  pageSize: 20,
  soundNotifications: true,
  emailNotifications: true,
  autoRefreshInterval: 30,
};

const STORAGE_KEY = 'sip_autodialer_general_settings';

const TIMEZONES = [
  'UTC',
  'America/New_York',
  'America/Chicago',
  'America/Denver',
  'America/Los_Angeles',
  'America/Phoenix',
  'America/Anchorage',
  'America/Jamaica',
  'Pacific/Honolulu',
  'Europe/London',
  'Europe/Paris',
  'Europe/Berlin',
  'Asia/Tokyo',
  'Asia/Shanghai',
  'Asia/Singapore',
  'Australia/Sydney',
];

const DATE_FORMATS = [
  { value: 'MM/DD/YYYY', label: 'MM/DD/YYYY (US)' },
  { value: 'DD/MM/YYYY', label: 'DD/MM/YYYY (EU)' },
  { value: 'YYYY-MM-DD', label: 'YYYY-MM-DD (ISO)' },
];

const PAGE_SIZES = [10, 20, 50, 100];

const AUTO_REFRESH_OPTIONS = [
  { value: 0, label: 'Disabled' },
  { value: 15, label: '15 seconds' },
  { value: 30, label: '30 seconds' },
  { value: 60, label: '1 minute' },
  { value: 300, label: '5 minutes' },
];

export function GeneralSettingsTab() {
  const [settings, setSettings] = useState<GeneralSettings>(DEFAULT_SETTINGS);
  const [isSaved, setIsSaved] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);

  // Load settings from localStorage on mount
  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      try {
        const parsed = JSON.parse(stored);
        setSettings({ ...DEFAULT_SETTINGS, ...parsed });
      } catch {
        // Use defaults if parsing fails
      }
    }
  }, []);

  const handleChange = <K extends keyof GeneralSettings>(
    key: K,
    value: GeneralSettings[K]
  ) => {
    setSettings((prev) => ({ ...prev, [key]: value }));
    setHasChanges(true);
    setIsSaved(false);
  };

  const handleSave = () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
    setIsSaved(true);
    setHasChanges(false);

    // Show saved message for 3 seconds
    setTimeout(() => setIsSaved(false), 3000);
  };

  const handleReset = () => {
    setSettings(DEFAULT_SETTINGS);
    setHasChanges(true);
    setIsSaved(false);
  };

  return (
    <div className="space-y-6">
      {/* Date & Time Settings */}
      <Card>
        <CardHeader>
          <CardTitle>Date & Time</CardTitle>
          <CardDescription>
            Configure how dates and times are displayed throughout the application.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="timezone">Timezone</Label>
              <Select
                value={settings.timezone}
                onValueChange={(value) => handleChange('timezone', value)}
              >
                <SelectTrigger id="timezone">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {TIMEZONES.map((tz) => (
                    <SelectItem key={tz} value={tz}>
                      {tz}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="dateFormat">Date Format</Label>
              <Select
                value={settings.dateFormat}
                onValueChange={(value) => handleChange('dateFormat', value)}
              >
                <SelectTrigger id="dateFormat">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {DATE_FORMATS.map((format) => (
                    <SelectItem key={format.value} value={format.value}>
                      {format.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="timeFormat">Time Format</Label>
              <Select
                value={settings.timeFormat}
                onValueChange={(value) => handleChange('timeFormat', value as '12h' | '24h')}
              >
                <SelectTrigger id="timeFormat">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="12h">12-hour (AM/PM)</SelectItem>
                  <SelectItem value="24h">24-hour</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Display Settings */}
      <Card>
        <CardHeader>
          <CardTitle>Display</CardTitle>
          <CardDescription>
            Configure display and pagination preferences.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="pageSize">Default Page Size</Label>
              <Select
                value={settings.pageSize.toString()}
                onValueChange={(value) => handleChange('pageSize', parseInt(value))}
              >
                <SelectTrigger id="pageSize">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {PAGE_SIZES.map((size) => (
                    <SelectItem key={size} value={size.toString()}>
                      {size} items per page
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="autoRefresh">Auto-Refresh Interval</Label>
              <Select
                value={settings.autoRefreshInterval.toString()}
                onValueChange={(value) => handleChange('autoRefreshInterval', parseInt(value))}
              >
                <SelectTrigger id="autoRefresh">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {AUTO_REFRESH_OPTIONS.map((option) => (
                    <SelectItem key={option.value} value={option.value.toString()}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                How often to refresh data on dashboard and campaign pages.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Notification Settings */}
      <Card>
        <CardHeader>
          <CardTitle>Notifications</CardTitle>
          <CardDescription>
            Configure how you receive notifications about campaign status and events.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label htmlFor="soundNotifications">Sound Notifications</Label>
              <p className="text-sm text-muted-foreground">
                Play sound alerts for important events
              </p>
            </div>
            <Switch
              id="soundNotifications"
              checked={settings.soundNotifications}
              onCheckedChange={(checked) => handleChange('soundNotifications', checked)}
            />
          </div>

          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label htmlFor="emailNotifications">Email Notifications</Label>
              <p className="text-sm text-muted-foreground">
                Receive email notifications for campaign completions and alerts
              </p>
            </div>
            <Switch
              id="emailNotifications"
              checked={settings.emailNotifications}
              onCheckedChange={(checked) => handleChange('emailNotifications', checked)}
            />
          </div>
        </CardContent>
      </Card>

      {/* System Information */}
      <Card>
        <CardHeader>
          <CardTitle>System Information</CardTitle>
          <CardDescription>
            Application version and system details.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <dl className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
            <div>
              <dt className="text-muted-foreground">Application Version</dt>
              <dd className="font-medium">1.0.0</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">API Version</dt>
              <dd className="font-medium">v1</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Browser Timezone</dt>
              <dd className="font-medium">
                {Intl.DateTimeFormat().resolvedOptions().timeZone}
              </dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Session Started</dt>
              <dd className="font-medium">
                {new Date().toLocaleString()}
              </dd>
            </div>
          </dl>
        </CardContent>
      </Card>

      {/* Save Button */}
      <div className="flex items-center justify-between">
        <Button variant="outline" onClick={handleReset}>
          Reset to Defaults
        </Button>
        <div className="flex items-center gap-4">
          {isSaved && (
            <span className="text-sm text-green-600">Settings saved successfully!</span>
          )}
          {hasChanges && !isSaved && (
            <span className="text-sm text-yellow-600">You have unsaved changes</span>
          )}
          <Button onClick={handleSave} disabled={!hasChanges}>
            Save Settings
          </Button>
        </div>
      </div>
    </div>
  );
}
