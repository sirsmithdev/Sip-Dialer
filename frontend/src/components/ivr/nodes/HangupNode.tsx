import { memo } from 'react';
import { NodeProps } from 'reactflow';
import { PhoneOff } from 'lucide-react';
import { BaseNode } from './BaseNode';
import { HangupNodeData } from '@/types/ivr';

export const HangupNode = memo(({ data, selected }: NodeProps<HangupNodeData>) => {
  return (
    <BaseNode
      title="Hangup"
      icon={<PhoneOff size={16} />}
      selected={selected}
      color="bg-gray-600"
      showSourceHandle={false}
    >
      {data.reason && (
        <p className="text-xs text-gray-600">{data.reason}</p>
      )}
    </BaseNode>
  );
});

HangupNode.displayName = 'HangupNode';
