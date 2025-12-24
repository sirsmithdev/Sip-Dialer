import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { contactsApi, audioApi } from '@/services/api';
import type { CampaignCreate, CampaignUpdate, Campaign, CampaignListItem, DialingMode, AMDAction } from '@/types';

interface CampaignFormProps {
  campaign?: Campaign | CampaignListItem;
  onSubmit: (data: CampaignCreate | CampaignUpdate) => void;
  onCancel: () => void;
  isSubmitting?: boolean;
}

// Type guard to check if campaign is full Campaign type
function isFullCampaign(c: Campaign | CampaignListItem): c is Campaign {
  return 'contact_list_id' in c;
}

export function CampaignForm({ campaign, onSubmit, onCancel, isSubmitting }: CampaignFormProps) {
  const isEdit = !!campaign;
  const fullCampaign = campaign && isFullCampaign(campaign) ? campaign : undefined;

  // Form state
  const [name, setName] = useState(campaign?.name || '');
  const [description, setDescription] = useState(campaign?.description || '');
  const [contactListId, setContactListId] = useState(fullCampaign?.contact_list_id || '');
  const [ivrFlowId] = useState(fullCampaign?.ivr_flow_id || '');
  const [greetingAudioId, setGreetingAudioId] = useState(fullCampaign?.greeting_audio_id || '');
  const [voicemailAudioId, setVoicemailAudioId] = useState(fullCampaign?.voicemail_audio_id || '');

  // Dialing settings
  const [dialingMode, setDialingMode] = useState<DialingMode>(campaign?.dialing_mode || 'progressive');
  const [maxConcurrentCalls, setMaxConcurrentCalls] = useState(fullCampaign?.max_concurrent_calls || 5);
  const [callsPerMinute, setCallsPerMinute] = useState(fullCampaign?.calls_per_minute || undefined);

  // Retry settings
  const [maxRetries, setMaxRetries] = useState(fullCampaign?.max_retries || 2);
  const [retryDelayMinutes, setRetryDelayMinutes] = useState(fullCampaign?.retry_delay_minutes || 30);
  const [retryOnNoAnswer, setRetryOnNoAnswer] = useState(fullCampaign?.retry_on_no_answer ?? true);
  const [retryOnBusy, setRetryOnBusy] = useState(fullCampaign?.retry_on_busy ?? true);
  const [retryOnFailed, setRetryOnFailed] = useState(fullCampaign?.retry_on_failed ?? false);

  // Call timing
  const [ringTimeoutSeconds, setRingTimeoutSeconds] = useState(fullCampaign?.ring_timeout_seconds || 30);

  // AMD settings
  const [amdEnabled, setAmdEnabled] = useState(fullCampaign?.amd_enabled ?? true);
  const [amdActionHuman, setAmdActionHuman] = useState<AMDAction>((fullCampaign?.amd_action_human as AMDAction) || 'play_ivr');
  const [amdActionMachine, setAmdActionMachine] = useState<AMDAction>((fullCampaign?.amd_action_machine as AMDAction) || 'leave_message');

  // Calling hours
  const [callingHoursStart, setCallingHoursStart] = useState(fullCampaign?.calling_hours_start || '09:00');
  const [callingHoursEnd, setCallingHoursEnd] = useState(fullCampaign?.calling_hours_end || '21:00');
  const [respectTimezone, setRespectTimezone] = useState(fullCampaign?.respect_timezone ?? true);

  // Fetch contact lists
  const { data: contactListsData } = useQuery({
    queryKey: ['contact-lists'],
    queryFn: () => contactsApi.listContactLists({ page_size: 100, is_active: true }),
  });

  // Fetch audio files
  const { data: audioFilesData } = useQuery({
    queryKey: ['audio-files'],
    queryFn: () => audioApi.list({ page_size: 100, is_active: true }),
  });

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();

    const data: CampaignCreate = {
      name,
      description: description || undefined,
      contact_list_id: contactListId,
      ivr_flow_id: ivrFlowId || undefined,
      greeting_audio_id: greetingAudioId || undefined,
      voicemail_audio_id: voicemailAudioId || undefined,
      dialing_mode: dialingMode,
      max_concurrent_calls: maxConcurrentCalls,
      calls_per_minute: callsPerMinute,
      max_retries: maxRetries,
      retry_delay_minutes: retryDelayMinutes,
      retry_on_no_answer: retryOnNoAnswer,
      retry_on_busy: retryOnBusy,
      retry_on_failed: retryOnFailed,
      ring_timeout_seconds: ringTimeoutSeconds,
      amd_enabled: amdEnabled,
      amd_action_human: amdActionHuman,
      amd_action_machine: amdActionMachine,
      calling_hours_start: callingHoursStart,
      calling_hours_end: callingHoursEnd,
      respect_timezone: respectTimezone,
    };

    onSubmit(data);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <Tabs defaultValue="basic" className="w-full">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="basic">Basic</TabsTrigger>
          <TabsTrigger value="dialing">Dialing</TabsTrigger>
          <TabsTrigger value="amd">AMD</TabsTrigger>
          <TabsTrigger value="tcpa">TCPA</TabsTrigger>
        </TabsList>

        <TabsContent value="basic" className="space-y-4 mt-4">
          <Card>
            <CardHeader>
              <CardTitle>Campaign Information</CardTitle>
              <CardDescription>Basic campaign settings and target contacts</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="name">Campaign Name *</Label>
                <Input
                  id="name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Enter campaign name"
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="description">Description</Label>
                <Textarea
                  id="description"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Enter campaign description"
                  rows={3}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="contact-list">Contact List *</Label>
                <Select value={contactListId} onValueChange={setContactListId} required>
                  <SelectTrigger>
                    <SelectValue placeholder="Select a contact list" />
                  </SelectTrigger>
                  <SelectContent>
                    {contactListsData?.items.map((list) => (
                      <SelectItem key={list.id} value={list.id}>
                        {list.name} ({list.valid_contacts} contacts)
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="greeting-audio">Greeting Audio</Label>
                <Select value={greetingAudioId} onValueChange={setGreetingAudioId}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select greeting audio (optional)" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">None</SelectItem>
                    {audioFilesData?.items
                      .filter((a) => a.status === 'ready')
                      .map((audio) => (
                        <SelectItem key={audio.id} value={audio.id}>
                          {audio.name}
                        </SelectItem>
                      ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="voicemail-audio">Voicemail Audio</Label>
                <Select value={voicemailAudioId} onValueChange={setVoicemailAudioId}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select voicemail audio (optional)" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">None</SelectItem>
                    {audioFilesData?.items
                      .filter((a) => a.status === 'ready')
                      .map((audio) => (
                        <SelectItem key={audio.id} value={audio.id}>
                          {audio.name}
                        </SelectItem>
                      ))}
                  </SelectContent>
                </Select>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="dialing" className="space-y-4 mt-4">
          <Card>
            <CardHeader>
              <CardTitle>Dialing Settings</CardTitle>
              <CardDescription>Configure call pacing and retry behavior</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="dialing-mode">Dialing Mode</Label>
                  <Select value={dialingMode} onValueChange={(v) => setDialingMode(v as DialingMode)}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="progressive">Progressive</SelectItem>
                      <SelectItem value="predictive">Predictive</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="max-concurrent">Max Concurrent Calls</Label>
                  <Input
                    id="max-concurrent"
                    type="number"
                    min={1}
                    max={100}
                    value={maxConcurrentCalls}
                    onChange={(e) => setMaxConcurrentCalls(Number(e.target.value))}
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="ring-timeout">Ring Timeout (seconds)</Label>
                  <Input
                    id="ring-timeout"
                    type="number"
                    min={10}
                    max={120}
                    value={ringTimeoutSeconds}
                    onChange={(e) => setRingTimeoutSeconds(Number(e.target.value))}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="calls-per-minute">Calls per Minute (optional)</Label>
                  <Input
                    id="calls-per-minute"
                    type="number"
                    min={1}
                    max={1000}
                    value={callsPerMinute || ''}
                    onChange={(e) => setCallsPerMinute(e.target.value ? Number(e.target.value) : undefined)}
                    placeholder="Unlimited"
                  />
                </div>
              </div>

              <div className="border-t pt-4 mt-4">
                <h4 className="font-medium mb-3">Retry Settings</h4>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="max-retries">Max Retries</Label>
                    <Input
                      id="max-retries"
                      type="number"
                      min={0}
                      max={10}
                      value={maxRetries}
                      onChange={(e) => setMaxRetries(Number(e.target.value))}
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="retry-delay">Retry Delay (minutes)</Label>
                    <Input
                      id="retry-delay"
                      type="number"
                      min={1}
                      max={1440}
                      value={retryDelayMinutes}
                      onChange={(e) => setRetryDelayMinutes(Number(e.target.value))}
                    />
                  </div>
                </div>

                <div className="space-y-3 mt-4">
                  <div className="flex items-center justify-between">
                    <Label htmlFor="retry-no-answer">Retry on No Answer</Label>
                    <Switch
                      id="retry-no-answer"
                      checked={retryOnNoAnswer}
                      onCheckedChange={setRetryOnNoAnswer}
                    />
                  </div>

                  <div className="flex items-center justify-between">
                    <Label htmlFor="retry-busy">Retry on Busy</Label>
                    <Switch
                      id="retry-busy"
                      checked={retryOnBusy}
                      onCheckedChange={setRetryOnBusy}
                    />
                  </div>

                  <div className="flex items-center justify-between">
                    <Label htmlFor="retry-failed">Retry on Failed</Label>
                    <Switch
                      id="retry-failed"
                      checked={retryOnFailed}
                      onCheckedChange={setRetryOnFailed}
                    />
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="amd" className="space-y-4 mt-4">
          <Card>
            <CardHeader>
              <CardTitle>Answering Machine Detection</CardTitle>
              <CardDescription>Configure AMD behavior and actions</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <Label htmlFor="amd-enabled">Enable AMD</Label>
                  <p className="text-sm text-muted-foreground">
                    Detect answering machines and take appropriate action
                  </p>
                </div>
                <Switch
                  id="amd-enabled"
                  checked={amdEnabled}
                  onCheckedChange={setAmdEnabled}
                />
              </div>

              {amdEnabled && (
                <>
                  <div className="space-y-2">
                    <Label htmlFor="amd-human">When Human Answers</Label>
                    <Select
                      value={amdActionHuman}
                      onValueChange={(v) => setAmdActionHuman(v as AMDAction)}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="play_ivr">Play IVR Flow</SelectItem>
                        <SelectItem value="leave_message">Play Message</SelectItem>
                        <SelectItem value="transfer">Transfer to Agent</SelectItem>
                        <SelectItem value="hangup">Hang Up</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="amd-machine">When Machine Answers</Label>
                    <Select
                      value={amdActionMachine}
                      onValueChange={(v) => setAmdActionMachine(v as AMDAction)}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="leave_message">Leave Voicemail</SelectItem>
                        <SelectItem value="play_ivr">Play IVR Flow</SelectItem>
                        <SelectItem value="hangup">Hang Up</SelectItem>
                        <SelectItem value="transfer">Transfer to Agent</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="tcpa" className="space-y-4 mt-4">
          <Card>
            <CardHeader>
              <CardTitle>TCPA Compliance</CardTitle>
              <CardDescription>Configure calling hours and timezone handling</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="calling-start">Calling Hours Start</Label>
                  <Input
                    id="calling-start"
                    type="time"
                    value={callingHoursStart}
                    onChange={(e) => setCallingHoursStart(e.target.value)}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="calling-end">Calling Hours End</Label>
                  <Input
                    id="calling-end"
                    type="time"
                    value={callingHoursEnd}
                    onChange={(e) => setCallingHoursEnd(e.target.value)}
                  />
                </div>
              </div>

              <div className="flex items-center justify-between">
                <div>
                  <Label htmlFor="respect-timezone">Respect Contact Timezone</Label>
                  <p className="text-sm text-muted-foreground">
                    Only call contacts during their local calling hours
                  </p>
                </div>
                <Switch
                  id="respect-timezone"
                  checked={respectTimezone}
                  onCheckedChange={setRespectTimezone}
                />
              </div>

              <div className="rounded-md bg-muted p-4 mt-4">
                <p className="text-sm">
                  <strong>TCPA Compliance:</strong> The Telephone Consumer Protection Act requires
                  calls to be made only between 8 AM and 9 PM in the recipient's local time. Ensure
                  your calling hours comply with federal and state regulations.
                </p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      <div className="flex justify-end gap-3 pt-4 border-t">
        <Button type="button" variant="outline" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" disabled={isSubmitting || !name || !contactListId}>
          {isSubmitting ? 'Saving...' : isEdit ? 'Update Campaign' : 'Create Campaign'}
        </Button>
      </div>
    </form>
  );
}
