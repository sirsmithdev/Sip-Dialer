import { memo } from 'react';
import { NodeProps } from 'reactflow';
import { ListTree } from 'lucide-react';
import { BaseNode } from './BaseNode';
import { MenuNodeData } from '@/types/ivr';

export const MenuNode = memo(({ data, selected }: NodeProps<MenuNodeData>) => {
  const optionCount = data.options ? Object.keys(data.options).length : 0;

  return (
    <BaseNode
      title="Menu"
      icon={<ListTree size={16} />}
      selected={selected}
      color="bg-blue-600"
    >
      <div className="space-y-1">
        {data.prompt_audio_name ? (
          <p className="font-medium text-xs">{data.prompt_audio_name}</p>
        ) : (
          <p className="text-gray-400 italic text-xs">No prompt selected</p>
        )}
        <div className="flex gap-2 text-xs text-gray-600">
          <span>{optionCount} options</span>
          {data.timeout && <span>• {data.timeout}s timeout</span>}
        </div>
        {data.max_retries && (
          <p className="text-xs text-gray-500">Max retries: {data.max_retries}</p>
        )}
      </div>
    </BaseNode>
  );
});

MenuNode.displayName = 'MenuNode';
