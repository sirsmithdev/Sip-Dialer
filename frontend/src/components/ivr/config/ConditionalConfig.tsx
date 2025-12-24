import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { ConditionalNodeData } from '@/types/ivr';

interface ConditionalConfigProps {
  data: ConditionalNodeData;
  onUpdate: (data: Record<string, unknown>) => void;
}

export function ConditionalConfig({ data, onUpdate }: ConditionalConfigProps) {
  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="variable_name">Variable Name</Label>
        <Input
          id="variable_name"
          placeholder="e.g., user_input"
          value={data.variable_name || ''}
          onChange={(e) => onUpdate({ variable_name: e.target.value })}
        />
        <p className="text-xs text-gray-500">
          The variable to check
        </p>
      </div>

      <div className="space-y-2">
        <Label htmlFor="operator">Operator</Label>
        <Select
          value={data.operator || 'equals'}
          onValueChange={(value) => onUpdate({ operator: value })}
        >
          <SelectTrigger id="operator">
            <SelectValue placeholder="Select operator" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="equals">Equals</SelectItem>
            <SelectItem value="not_equals">Not Equals</SelectItem>
            <SelectItem value="greater_than">Greater Than</SelectItem>
            <SelectItem value="less_than">Less Than</SelectItem>
            <SelectItem value="contains">Contains</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-2">
        <Label htmlFor="value">Value</Label>
        <Input
          id="value"
          placeholder="Value to compare"
          value={data.value || ''}
          onChange={(e) => onUpdate({ value: e.target.value })}
        />
      </div>

      <div className="space-y-2">
        <Label>Branching</Label>
        <p className="text-xs text-gray-500">
          Connect this node to two other nodes: one for true condition (left handle) and one for false condition (right handle).
        </p>
      </div>
    </div>
  );
}
