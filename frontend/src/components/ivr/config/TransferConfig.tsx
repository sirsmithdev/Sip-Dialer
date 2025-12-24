import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { TransferNodeData } from '@/types/ivr';

interface TransferConfigProps {
  data: TransferNodeData;
  onUpdate: (data: Record<string, unknown>) => void;
}

export function TransferConfig({ data, onUpdate }: TransferConfigProps) {
  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="destination">Destination Number</Label>
        <Input
          id="destination"
          placeholder="e.g., +1234567890"
          value={data.destination_number || ''}
          onChange={(e) => onUpdate({ destination_number: e.target.value })}
        />
        <p className="text-xs text-gray-500">
          Phone number to transfer the call to
        </p>
      </div>

      <div className="space-y-2">
        <Label htmlFor="timeout">Timeout (seconds)</Label>
        <Input
          id="timeout"
          type="number"
          min="5"
          max="120"
          value={data.timeout_seconds || 30}
          onChange={(e) => onUpdate({ timeout_seconds: parseInt(e.target.value) })}
        />
        <p className="text-xs text-gray-500">
          How long to ring before giving up
        </p>
      </div>

      <div className="space-y-2">
        <Label htmlFor="caller_id">Caller ID (optional)</Label>
        <Input
          id="caller_id"
          placeholder="e.g., +1234567890"
          value={data.caller_id || ''}
          onChange={(e) => onUpdate({ caller_id: e.target.value })}
        />
        <p className="text-xs text-gray-500">
          Custom caller ID to display
        </p>
      </div>
    </div>
  );
}
