import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Phone, Volume2, Voicemail, CheckCircle2, XCircle, Loader2, AlertCircle } from 'lucide-react';
import { sipSettingsApi, audioApi } from '@/services/api';
import type { AudioFile } from '@/types';

export function TestCallSettings() {
  const [phoneNumber, setPhoneNumber] = useState('');
  const [callerId, setCallerId] = useState('');
  const [audioFileId, setAudioFileId] = useState<string>('');
  const [voicemailAudioFileId, setVoicemailAudioFileId] = useState<string>('');

  // Fetch dialer status
  const { data: dialerStatus, isLoading: statusLoading } = useQuery({
    queryKey: ['dialerStatus'],
    queryFn: sipSettingsApi.getDialerStatus,
    refetchInterval: 5000, // Refresh every 5 seconds
  });

  // Fetch audio files for selection
  const { data: audioFiles, isLoading: audioLoading } = useQuery({
    queryKey: ['audioFiles', { is_active: true }],
    queryFn: () => audioApi.list({ is_active: true, page_size: 100 }),
  });

  // Make test call mutation
  const testCallMutation = useMutation({
    mutationFn: (params: {
      phone_number: string;
      caller_id?: string;
      audio_file?: string;
      voicemail_audio_file?: string;
    }) => sipSettingsApi.makeTestCall(params),
  });

  const handleMakeTestCall = () => {
    if (!phoneNumber) return;

    testCallMutation.mutate({
      phone_number: phoneNumber,
      caller_id: callerId || undefined,
      audio_file: audioFileId && audioFileId !== 'none' ? audioFileId : undefined,
      voicemail_audio_file: voicemailAudioFileId && voicemailAudioFileId !== 'none' ? voicemailAudioFileId : undefined,
    });
  };

  const isDialerOnline = dialerStatus?.is_online ?? false;
  const sipStatus = dialerStatus?.sip?.status ?? 'unknown';

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'registered':
      case 'connected':
        return 'bg-green-500';
      case 'connecting':
        return 'bg-yellow-500';
      case 'failed':
      case 'disconnected':
        return 'bg-red-500';
      default:
        return 'bg-gray-500';
    }
  };

  const activeAudioFiles = audioFiles?.items?.filter((f: AudioFile) => f.is_active && f.status === 'ready') ?? [];

  return (
    <div className="space-y-6">
      {/* Dialer Status Card */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Phone className="h-5 w-5" />
            Dialer Status
          </CardTitle>
          <CardDescription>
            Current status of the SIP dialer connection
          </CardDescription>
        </CardHeader>
        <CardContent>
          {statusLoading ? (
            <div className="flex items-center gap-2 text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              Loading status...
            </div>
          ) : (
            <div className="space-y-4">
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-2">
                  <div className={`h-3 w-3 rounded-full ${isDialerOnline ? 'bg-green-500' : 'bg-red-500'}`} />
                  <span className="font-medium">
                    Dialer: {isDialerOnline ? 'Online' : 'Offline'}
                  </span>
                </div>
                <Badge variant="outline" className="flex items-center gap-1">
                  <div className={`h-2 w-2 rounded-full ${getStatusColor(sipStatus)}`} />
                  SIP: {sipStatus}
                </Badge>
              </div>

              {dialerStatus?.sip && (
                <div className="grid grid-cols-2 gap-4 text-sm">
                  {dialerStatus.sip.extension && (
                    <div>
                      <span className="text-muted-foreground">Extension:</span>{' '}
                      <span className="font-medium">{dialerStatus.sip.extension}</span>
                    </div>
                  )}
                  {dialerStatus.sip.server && (
                    <div>
                      <span className="text-muted-foreground">Server:</span>{' '}
                      <span className="font-medium">{dialerStatus.sip.server}</span>
                    </div>
                  )}
                  {dialerStatus.sip.active_calls !== undefined && (
                    <div>
                      <span className="text-muted-foreground">Active Calls:</span>{' '}
                      <span className="font-medium">{dialerStatus.sip.active_calls}</span>
                    </div>
                  )}
                </div>
              )}

              {dialerStatus?.sip?.error && (
                <Alert variant="destructive">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>{dialerStatus.sip.error}</AlertDescription>
                </Alert>
              )}

              {!isDialerOnline && (
                <Alert>
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>
                    The dialer service is offline. Please check your SIP configuration and ensure the dialer is running.
                  </AlertDescription>
                </Alert>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Test Call Card */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Phone className="h-5 w-5" />
            Make Test Call
          </CardTitle>
          <CardDescription>
            Place a test call to verify audio playback and voicemail detection
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-6">
            {/* Phone Number */}
            <div className="space-y-2">
              <Label htmlFor="phone_number">Phone Number *</Label>
              <Input
                id="phone_number"
                placeholder="+15551234567"
                value={phoneNumber}
                onChange={(e) => setPhoneNumber(e.target.value)}
                disabled={!isDialerOnline}
              />
              <p className="text-xs text-muted-foreground">
                Enter the phone number to call (include country code)
              </p>
            </div>

            {/* Caller ID */}
            <div className="space-y-2">
              <Label htmlFor="caller_id">Caller ID (Optional)</Label>
              <Input
                id="caller_id"
                placeholder="Leave empty to use default"
                value={callerId}
                onChange={(e) => setCallerId(e.target.value)}
                disabled={!isDialerOnline}
              />
              <p className="text-xs text-muted-foreground">
                Override the caller ID for this test call
              </p>
            </div>

            {/* Human Answer Audio */}
            <div className="space-y-2">
              <Label htmlFor="audio_file" className="flex items-center gap-2">
                <Volume2 className="h-4 w-4" />
                Audio for Human Answer
              </Label>
              <Select
                value={audioFileId}
                onValueChange={setAudioFileId}
                disabled={!isDialerOnline || audioLoading}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select audio file..." />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">No audio (silence)</SelectItem>
                  {activeAudioFiles.map((file: AudioFile) => (
                    <SelectItem key={file.id} value={file.id}>
                      {file.name}
                      {file.duration_seconds && (
                        <span className="ml-2 text-muted-foreground">
                          ({Math.round(file.duration_seconds)}s)
                        </span>
                      )}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                Audio to play when a human answers the call
              </p>
            </div>

            {/* Voicemail/Machine Audio */}
            <div className="space-y-2">
              <Label htmlFor="voicemail_audio" className="flex items-center gap-2">
                <Voicemail className="h-4 w-4" />
                Audio for Voicemail/Machine
              </Label>
              <Select
                value={voicemailAudioFileId}
                onValueChange={setVoicemailAudioFileId}
                disabled={!isDialerOnline || audioLoading}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select audio file..." />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">No audio (hang up)</SelectItem>
                  {activeAudioFiles.map((file: AudioFile) => (
                    <SelectItem key={file.id} value={file.id}>
                      {file.name}
                      {file.duration_seconds && (
                        <span className="ml-2 text-muted-foreground">
                          ({Math.round(file.duration_seconds)}s)
                        </span>
                      )}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                Audio to play when voicemail or answering machine is detected
              </p>
            </div>

            {/* Make Call Button */}
            <Button
              onClick={handleMakeTestCall}
              disabled={!isDialerOnline || !phoneNumber || testCallMutation.isPending}
              className="w-full"
            >
              {testCallMutation.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Initiating Call...
                </>
              ) : (
                <>
                  <Phone className="mr-2 h-4 w-4" />
                  Make Test Call
                </>
              )}
            </Button>

            {/* Result Display */}
            {testCallMutation.data && (
              <Alert variant={testCallMutation.data.success ? 'default' : 'destructive'}>
                {testCallMutation.data.success ? (
                  <CheckCircle2 className="h-4 w-4" />
                ) : (
                  <XCircle className="h-4 w-4" />
                )}
                <AlertDescription>
                  {testCallMutation.data.message}
                </AlertDescription>
              </Alert>
            )}

            {testCallMutation.error && (
              <Alert variant="destructive">
                <XCircle className="h-4 w-4" />
                <AlertDescription>
                  Failed to initiate test call. Please check your connection and try again.
                </AlertDescription>
              </Alert>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Instructions Card */}
      <Card>
        <CardHeader>
          <CardTitle>How Test Calls Work</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground space-y-2">
          <p>
            1. The dialer will place a call to the specified phone number.
          </p>
          <p>
            2. When the call is answered, the system uses AMD (Answering Machine Detection) to determine if a human or machine answered.
          </p>
          <p>
            3. Based on the detection result, the appropriate audio file will be played.
          </p>
          <p>
            4. If no audio file is selected, the call will either be silent (human) or hang up (voicemail).
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
