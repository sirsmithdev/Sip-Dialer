import { memo } from 'react';
import { NodeProps } from 'reactflow';
import { Volume2 } from 'lucide-react';
import { BaseNode } from './BaseNode';
import { PlayAudioNodeData } from '@/types/ivr';

export const PlayAudioNode = memo(({ data, selected }: NodeProps<PlayAudioNodeData>) => {
  return (
    <BaseNode
      title="Play Audio"
      icon={<Volume2 size={16} />}
      selected={selected}
      color="bg-purple-600"
    >
      <div className="space-y-1">
        {data.audio_file_name ? (
          <p className="font-medium">{data.audio_file_name}</p>
        ) : (
          <p className="text-gray-400 italic">No audio selected</p>
        )}
        {data.wait_for_dtmf && (
          <p className="text-xs text-gray-500">Wait for DTMF input</p>
        )}
      </div>
    </BaseNode>
  );
});

PlayAudioNode.displayName = 'PlayAudioNode';
