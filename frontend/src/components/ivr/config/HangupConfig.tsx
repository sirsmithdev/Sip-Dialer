import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { HangupNodeData } from '@/types/ivr';

interface HangupConfigProps {
  data: HangupNodeData;
  onUpdate: (data: Record<string, unknown>) => void;
}

export function HangupConfig({ data, onUpdate }: HangupConfigProps) {
  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="reason">Reason (optional)</Label>
        <Input
          id="reason"
          placeholder="e.g., Call completed"
          value={data.reason || ''}
          onChange={(e) => onUpdate({ reason: e.target.value })}
        />
        <p className="text-xs text-gray-500">
          Optional reason for ending the call (for logging)
        </p>
      </div>

      <div className="text-sm text-gray-500">
        This node will end the call. No further nodes will be executed after this point.
      </div>
    </div>
  );
}
