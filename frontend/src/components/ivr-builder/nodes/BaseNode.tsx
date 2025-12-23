import { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import { cn } from '@/lib/utils';
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
  UserMinus,
  type LucideIcon,
} from 'lucide-react';
import type { IVRNodeData, IVRNodeType } from '../types';

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
  UserMinus,
};

const nodeStyles: Record<IVRNodeType, { bg: string; border: string; icon: string }> = {
  start: { bg: 'bg-green-500/10', border: 'border-green-500', icon: 'Play' },
  play_audio: { bg: 'bg-blue-500/10', border: 'border-blue-500', icon: 'Volume2' },
  menu: { bg: 'bg-purple-500/10', border: 'border-purple-500', icon: 'List' },
  survey_question: { bg: 'bg-orange-500/10', border: 'border-orange-500', icon: 'HelpCircle' },
  record: { bg: 'bg-red-500/10', border: 'border-red-500', icon: 'Mic' },
  transfer: { bg: 'bg-cyan-500/10', border: 'border-cyan-500', icon: 'PhoneForwarded' },
  conditional: { bg: 'bg-yellow-500/10', border: 'border-yellow-500', icon: 'GitBranch' },
  set_variable: { bg: 'bg-indigo-500/10', border: 'border-indigo-500', icon: 'Variable' },
  hangup: { bg: 'bg-gray-500/10', border: 'border-gray-500', icon: 'PhoneOff' },
  opt_out: { bg: 'bg-rose-500/10', border: 'border-rose-500', icon: 'UserMinus' },
};

interface BaseNodeProps {
  data: IVRNodeData;
  selected?: boolean;
}

function BaseNodeComponent({ data, selected }: BaseNodeProps) {
  const nodeType = data.type;
  const style = nodeStyles[nodeType];
  const Icon = iconMap[style.icon];

  const isStart = nodeType === 'start';
  // Opt-out can be an end node if hangupAfter is true (default)
  const isOptOutEnd = nodeType === 'opt_out' && (data as { hangupAfter?: boolean }).hangupAfter !== false;
  const isEnd = nodeType === 'hangup' || isOptOutEnd;
  const hasMultipleOutputs = nodeType === 'menu' || nodeType === 'conditional';

  return (
    <div
      className={cn(
        'rounded-lg border-2 shadow-lg min-w-[180px] transition-all duration-200',
        style.bg,
        style.border,
        selected && 'ring-2 ring-primary ring-offset-2 ring-offset-background'
      )}
    >
      {/* Input Handle */}
      {!isStart && (
        <Handle
          type="target"
          position={Position.Top}
          className="!w-3 !h-3 !bg-muted-foreground !border-2 !border-background"
        />
      )}

      {/* Node Content */}
      <div className="p-3">
        {/* Header */}
        <div className="flex items-center gap-2 mb-1">
          <div className={cn('w-7 h-7 rounded-md flex items-center justify-center', style.border.replace('border-', 'bg-').replace('500', '500/20'))}>
            {Icon && <Icon className="w-4 h-4" />}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold truncate">{data.label}</p>
            <p className="text-xs text-muted-foreground capitalize">{nodeType.replace('_', ' ')}</p>
          </div>
        </div>

        {/* Node-specific content preview */}
        <NodeContent data={data} />
      </div>

      {/* Output Handle(s) */}
      {!isEnd && !hasMultipleOutputs && (
        <Handle
          type="source"
          position={Position.Bottom}
          className="!w-3 !h-3 !bg-primary !border-2 !border-background"
        />
      )}

      {/* Multiple output handles for menu/conditional */}
      {hasMultipleOutputs && (
        <div className="flex justify-around pb-2">
          <Handle
            type="source"
            position={Position.Bottom}
            id="default"
            className="!w-3 !h-3 !bg-primary !border-2 !border-background !relative !transform-none !left-auto !-bottom-1"
          />
        </div>
      )}
    </div>
  );
}

function NodeContent({ data }: { data: IVRNodeData }) {
  switch (data.type) {
    case 'play_audio':
      return data.audioFileName ? (
        <p className="text-xs text-muted-foreground mt-2 truncate">
          {data.audioFileName}
        </p>
      ) : null;

    case 'menu':
      const optionCount = Object.keys(data.options || {}).length;
      return (
        <p className="text-xs text-muted-foreground mt-2">
          {optionCount} option{optionCount !== 1 ? 's' : ''} • {data.timeout}s timeout
        </p>
      );

    case 'survey_question':
      return data.questionId ? (
        <p className="text-xs text-muted-foreground mt-2 truncate">
          Q: {data.questionId}
        </p>
      ) : null;

    case 'transfer':
      return data.destination ? (
        <p className="text-xs text-muted-foreground mt-2 truncate">
          → {data.destination}
        </p>
      ) : null;

    case 'conditional':
      return data.variable ? (
        <p className="text-xs text-muted-foreground mt-2 truncate">
          {data.variable} {data.operator} {data.value}
        </p>
      ) : null;

    case 'set_variable':
      return data.variableName ? (
        <p className="text-xs text-muted-foreground mt-2 truncate">
          {data.variableName} = {data.value}
        </p>
      ) : null;

    case 'record':
      return (
        <p className="text-xs text-muted-foreground mt-2">
          Max {data.maxDuration}s
        </p>
      );

    case 'opt_out':
      return (
        <p className="text-xs text-rose-600 dark:text-rose-400 mt-2">
          Adds to DNC list
        </p>
      );

    default:
      return null;
  }
}

export const BaseNode = memo(BaseNodeComponent);
