import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { MenuNodeData } from '@/types/ivr';

interface MenuConfigProps {
  data: MenuNodeData;
  onUpdate: (data: Record<string, unknown>) => void;
}

export function MenuConfig({ data, onUpdate }: MenuConfigProps) {
  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="prompt_audio">Prompt Audio</Label>
        <Input
          id="prompt_audio"
          placeholder="Select prompt audio..."
          value={data.prompt_audio_name || ''}
          onChange={(e) => onUpdate({ prompt_audio_name: e.target.value })}
        />
        <p className="text-xs text-gray-500">
          Audio file that presents menu options to caller
        </p>
      </div>

      <div className="space-y-2">
        <Label htmlFor="timeout">Timeout (seconds)</Label>
        <Input
          id="timeout"
          type="number"
          min="1"
          max="60"
          value={data.timeout || 5}
          onChange={(e) => onUpdate({ timeout: parseInt(e.target.value) })}
        />
        <p className="text-xs text-gray-500">
          How long to wait for caller input
        </p>
      </div>

      <div className="space-y-2">
        <Label htmlFor="max_retries">Max Retries</Label>
        <Input
          id="max_retries"
          type="number"
          min="1"
          max="10"
          value={data.max_retries || 3}
          onChange={(e) => onUpdate({ max_retries: parseInt(e.target.value) })}
        />
        <p className="text-xs text-gray-500">
          Number of times to retry on invalid input
        </p>
      </div>

      <div className="space-y-2">
        <Label>Menu Options</Label>
        <p className="text-xs text-gray-500">
          Connect this node to other nodes to create menu options. Each outgoing connection represents a menu choice.
        </p>
      </div>
    </div>
  );
}
