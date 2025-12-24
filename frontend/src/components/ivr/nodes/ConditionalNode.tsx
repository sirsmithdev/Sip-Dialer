import { memo } from 'react';
import { NodeProps } from 'reactflow';
import { GitBranch } from 'lucide-react';
import { BaseNode } from './BaseNode';
import { ConditionalNodeData } from '@/types/ivr';

export const ConditionalNode = memo(({ data, selected }: NodeProps<ConditionalNodeData>) => {
  return (
    <BaseNode
      title="Conditional"
      icon={<GitBranch size={16} />}
      selected={selected}
      color="bg-yellow-600"
    >
      <div className="space-y-1">
        {data.variable_name && data.operator && data.value ? (
          <>
            <p className="text-xs font-mono">
              {data.variable_name} {data.operator} {data.value}
            </p>
          </>
        ) : (
          <p className="text-gray-400 italic text-xs">No condition set</p>
        )}
      </div>
    </BaseNode>
  );
});

ConditionalNode.displayName = 'ConditionalNode';
