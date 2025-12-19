import { memo } from 'react';
import {
  Play,
  Volume2,
  List,
  HelpCircle,
  Mic,
  PhoneForwarded,
  GitBranch,
  Variable,
  PhoneOff,
  type LucideIcon,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { NODE_CONFIGS, type NodeConfig } from './types';

const iconMap: Record<string, LucideIcon> = {
  Play,
  Volume2,
  List,
  HelpCircle,
  Mic,
  PhoneForwarded,
  GitBranch,
  Variable,
  PhoneOff,
};

interface NodeToolbarProps {
  onDragStart: (event: React.DragEvent, nodeConfig: NodeConfig) => void;
}

function NodeToolbarComponent({ onDragStart }: NodeToolbarProps) {
  return (
    <div className="w-64 bg-card border-r border-border flex flex-col h-full">
      <div className="p-4 border-b border-border">
        <h3 className="font-semibold text-sm">IVR Nodes</h3>
        <p className="text-xs text-muted-foreground mt-1">
          Drag nodes to the canvas
        </p>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {NODE_CONFIGS.map((config) => {
          const Icon = iconMap[config.icon];
          return (
            <div
              key={config.type}
              draggable
              onDragStart={(e) => onDragStart(e, config)}
              className={cn(
                'flex items-center gap-3 p-3 rounded-lg border cursor-grab active:cursor-grabbing',
                'bg-muted/50 border-border hover:border-primary/50 hover:bg-muted',
                'transition-all duration-200'
              )}
            >
              <div className={cn('w-9 h-9 rounded-lg flex items-center justify-center text-white', config.color)}>
                {Icon && <Icon className="w-5 h-5" />}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium">{config.label}</p>
                <p className="text-xs text-muted-foreground truncate">
                  {config.description}
                </p>
              </div>
            </div>
          );
        })}
      </div>

      <div className="p-4 border-t border-border bg-muted/30">
        <p className="text-xs text-muted-foreground">
          <strong>Tip:</strong> Connect nodes by dragging from handles
        </p>
      </div>
    </div>
  );
}

export const NodeToolbar = memo(NodeToolbarComponent);
