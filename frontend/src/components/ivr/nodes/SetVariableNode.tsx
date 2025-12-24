import { memo } from 'react';
import { NodeProps } from 'reactflow';
import { Variable } from 'lucide-react';
import { BaseNode } from './BaseNode';
import { SetVariableNodeData } from '@/types/ivr';

export const SetVariableNode = memo(({ data, selected }: NodeProps<SetVariableNodeData>) => {
  return (
    <BaseNode
      title="Set Variable"
      icon={<Variable size={16} />}
      selected={selected}
      color="bg-teal-600"
    >
      <div className="space-y-1">
        {data.variable_name && data.value ? (
          <p className="text-xs font-mono">
            {data.variable_name} = {data.value}
          </p>
        ) : (
          <p className="text-gray-400 italic text-xs">No variable set</p>
        )}
        {data.value_type && (
          <p className="text-xs text-gray-500">Type: {data.value_type}</p>
        )}
      </div>
    </BaseNode>
  );
});

SetVariableNode.displayName = 'SetVariableNode';
