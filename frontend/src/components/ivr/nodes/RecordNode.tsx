import { memo } from 'react';
import { NodeProps } from 'reactflow';
import { Mic } from 'lucide-react';
import { BaseNode } from './BaseNode';
import { RecordNodeData } from '@/types/ivr';

export const RecordNode = memo(({ data, selected }: NodeProps<RecordNodeData>) => {
  return (
    <BaseNode
      title="Record"
      icon={<Mic size={16} />}
      selected={selected}
      color="bg-red-600"
    >
      <div className="space-y-1">
        {data.max_duration_seconds && (
          <p className="text-xs text-gray-600">Max duration: {data.max_duration_seconds}s</p>
        )}
        {data.beep_before_recording && (
          <p className="text-xs text-gray-500">Beep before recording</p>
        )}
        {data.finish_on_key && (
          <p className="text-xs text-gray-500">Finish on key: {data.finish_on_key}</p>
        )}
      </div>
    </BaseNode>
  );
});

RecordNode.displayName = 'RecordNode';
