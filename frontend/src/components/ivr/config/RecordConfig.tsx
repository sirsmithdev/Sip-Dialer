import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Switch } from '@/components/ui/switch';
import { RecordNodeData } from '@/types/ivr';

interface RecordConfigProps {
  data: RecordNodeData;
  onUpdate: (data: Record<string, unknown>) => void;
}

export function RecordConfig({ data, onUpdate }: RecordConfigProps) {
  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="max_duration">Max Duration (seconds)</Label>
        <Input
          id="max_duration"
          type="number"
          min="1"
          max="300"
          value={data.max_duration_seconds || 30}
          onChange={(e) => onUpdate({ max_duration_seconds: parseInt(e.target.value) })}
        />
        <p className="text-xs text-gray-500">
          Maximum recording length
        </p>
      </div>

      <div className="flex items-center space-x-2">
        <Switch
          id="beep_before"
          checked={data.beep_before_recording || false}
          onCheckedChange={(checked) => onUpdate({ beep_before_recording: checked })}
        />
        <Label htmlFor="beep_before">Play beep before recording</Label>
      </div>

      <div className="space-y-2">
        <Label htmlFor="finish_key">Finish on Key</Label>
        <Input
          id="finish_key"
          placeholder="e.g., #"
          maxLength={1}
          value={data.finish_on_key || '#'}
          onChange={(e) => onUpdate({ finish_on_key: e.target.value })}
        />
        <p className="text-xs text-gray-500">
          DTMF key to end recording early
        </p>
      </div>

      <div className="space-y-2">
        <Label htmlFor="timeout">Timeout (seconds)</Label>
        <Input
          id="timeout"
          type="number"
          min="1"
          max="60"
          value={data.timeout_seconds || 5}
          onChange={(e) => onUpdate({ timeout_seconds: parseInt(e.target.value) })}
        />
        <p className="text-xs text-gray-500">
          Silence timeout before stopping recording
        </p>
      </div>
    </div>
  );
}
