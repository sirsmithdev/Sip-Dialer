import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { SetVariableNodeData } from '@/types/ivr';

interface SetVariableConfigProps {
  data: SetVariableNodeData;
  onUpdate: (data: Record<string, unknown>) => void;
}

export function SetVariableConfig({ data, onUpdate }: SetVariableConfigProps) {
  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="variable_name">Variable Name</Label>
        <Input
          id="variable_name"
          placeholder="e.g., customer_type"
          value={data.variable_name || ''}
          onChange={(e) => onUpdate({ variable_name: e.target.value })}
        />
        <p className="text-xs text-gray-500">
          Name of the variable to set
        </p>
      </div>

      <div className="space-y-2">
        <Label htmlFor="value_type">Value Type</Label>
        <Select
          value={data.value_type || 'static'}
          onValueChange={(value) => onUpdate({ value_type: value })}
        >
          <SelectTrigger id="value_type">
            <SelectValue placeholder="Select type" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="static">Static Value</SelectItem>
            <SelectItem value="dtmf_input">DTMF Input</SelectItem>
            <SelectItem value="call_variable">Call Variable</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-2">
        <Label htmlFor="value">Value</Label>
        <Input
          id="value"
          placeholder="Enter value"
          value={data.value || ''}
          onChange={(e) => onUpdate({ value: e.target.value })}
        />
        <p className="text-xs text-gray-500">
          {data.value_type === 'static' && 'Fixed value to assign'}
          {data.value_type === 'dtmf_input' && 'Capture DTMF input from caller'}
          {data.value_type === 'call_variable' && 'Copy from another variable'}
        </p>
      </div>
    </div>
  );
}
