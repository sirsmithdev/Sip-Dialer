import { memo } from 'react';
import { NodeProps } from 'reactflow';
import { Play } from 'lucide-react';
import { BaseNode } from './BaseNode';
import { BaseNodeData } from '@/types/ivr';

export const StartNode = memo(({ selected }: NodeProps<BaseNodeData>) => {
  return (
    <BaseNode
      title="Start"
      icon={<Play size={16} />}
      selected={selected}
      color="bg-green-600"
      showTargetHandle={false}
    >
      <p className="text-xs text-gray-500">Entry point of the IVR flow</p>
    </BaseNode>
  );
});

StartNode.displayName = 'StartNode';
