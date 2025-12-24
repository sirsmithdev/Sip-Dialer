import { memo } from 'react';
import { NodeProps } from 'reactflow';
import { PhoneForwarded } from 'lucide-react';
import { BaseNode } from './BaseNode';
import { TransferNodeData } from '@/types/ivr';

export const TransferNode = memo(({ data, selected }: NodeProps<TransferNodeData>) => {
  return (
    <BaseNode
      title="Transfer"
      icon={<PhoneForwarded size={16} />}
      selected={selected}
      color="bg-orange-600"
    >
      <div className="space-y-1">
        {data.destination_number ? (
          <p className="font-medium">{data.destination_number}</p>
        ) : (
          <p className="text-gray-400 italic">No destination</p>
        )}
        {data.timeout_seconds && (
          <p className="text-xs text-gray-500">Timeout: {data.timeout_seconds}s</p>
        )}
      </div>
    </BaseNode>
  );
});

TransferNode.displayName = 'TransferNode';
