import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Switch } from '@/components/ui/switch';
import { PlayAudioNodeData } from '@/types/ivr';

interface PlayAudioConfigProps {
  data: PlayAudioNodeData;
  onUpdate: (data: Record<string, unknown>) => void;
}

export function PlayAudioConfig({ data, onUpdate }: PlayAudioConfigProps) {
  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="audio_file">Audio File</Label>
        <Input
          id="audio_file"
          placeholder="Select audio file..."
          value={data.audio_file_name || ''}
          onChange={(e) => onUpdate({ audio_file_name: e.target.value })}
        />
        <p className="text-xs text-gray-500">
          Choose an audio file to play to the caller
        </p>
      </div>

      <div className="flex items-center space-x-2">
        <Switch
          id="wait_for_dtmf"
          checked={data.wait_for_dtmf || false}
          onCheckedChange={(checked) => onUpdate({ wait_for_dtmf: checked })}
        />
        <Label htmlFor="wait_for_dtmf">Wait for DTMF input</Label>
      </div>
    </div>
  );
}
