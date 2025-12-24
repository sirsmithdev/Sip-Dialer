import { memo, ReactNode } from 'react';
import { Handle, Position } from 'reactflow';
import { cn } from '@/lib/utils';

interface BaseNodeProps {
  title: string;
  icon: ReactNode;
  children?: ReactNode;
  selected?: boolean;
  color?: string;
  showSourceHandle?: boolean;
  showTargetHandle?: boolean;
}

export const BaseNode = memo(({
  title,
  icon,
  children,
  selected,
  color = 'bg-blue-500',
  showSourceHandle = true,
  showTargetHandle = true,
}: BaseNodeProps) => {
  return (
    <div
      className={cn(
        'rounded-lg border-2 bg-white shadow-lg min-w-[200px] transition-all',
        selected ? 'border-blue-500 shadow-xl' : 'border-gray-300'
      )}
    >
      {showTargetHandle && (
        <Handle
          type="target"
          position={Position.Top}
          className="w-3 h-3 !bg-gray-400"
        />
      )}

      <div className={cn('px-4 py-2 rounded-t-md text-white flex items-center gap-2', color)}>
        {icon}
        <span className="font-medium text-sm">{title}</span>
      </div>

      {children && (
        <div className="px-4 py-3 text-sm text-gray-700">
          {children}
        </div>
      )}

      {showSourceHandle && (
        <Handle
          type="source"
          position={Position.Bottom}
          className="w-3 h-3 !bg-gray-400"
        />
      )}
    </div>
  );
});

BaseNode.displayName = 'BaseNode';
