import {
  Volume2,
  ListTree,
  MessageSquareQuote,
  Mic,
  PhoneForwarded,
  GitBranch,
  Variable,
  PhoneOff,
} from 'lucide-react';
import { IVRNodeType } from '@/types/ivr';

interface NodePaletteProps {
  onAddNode: (type: IVRNodeType) => void;
}

const nodeDefinitions = [
  {
    type: 'play_audio' as IVRNodeType,
    label: 'Play Audio',
    description: 'Play an audio file',
    icon: Volume2,
    color: 'bg-purple-100 hover:bg-purple-200 border-purple-300',
  },
  {
    type: 'menu' as IVRNodeType,
    label: 'Menu',
    description: 'Present options to caller',
    icon: ListTree,
    color: 'bg-blue-100 hover:bg-blue-200 border-blue-300',
  },
  {
    type: 'survey_question' as IVRNodeType,
    label: 'Survey Question',
    description: 'Ask a survey question',
    icon: MessageSquareQuote,
    color: 'bg-indigo-100 hover:bg-indigo-200 border-indigo-300',
  },
  {
    type: 'record' as IVRNodeType,
    label: 'Record',
    description: 'Record caller audio',
    icon: Mic,
    color: 'bg-red-100 hover:bg-red-200 border-red-300',
  },
  {
    type: 'transfer' as IVRNodeType,
    label: 'Transfer',
    description: 'Transfer call to another number',
    icon: PhoneForwarded,
    color: 'bg-orange-100 hover:bg-orange-200 border-orange-300',
  },
  {
    type: 'conditional' as IVRNodeType,
    label: 'Conditional',
    description: 'Branch based on condition',
    icon: GitBranch,
    color: 'bg-yellow-100 hover:bg-yellow-200 border-yellow-300',
  },
  {
    type: 'set_variable' as IVRNodeType,
    label: 'Set Variable',
    description: 'Set a call variable',
    icon: Variable,
    color: 'bg-teal-100 hover:bg-teal-200 border-teal-300',
  },
  {
    type: 'hangup' as IVRNodeType,
    label: 'Hangup',
    description: 'End the call',
    icon: PhoneOff,
    color: 'bg-gray-100 hover:bg-gray-200 border-gray-300',
  },
];

export function NodePalette({ onAddNode }: NodePaletteProps) {
  return (
    <div className="space-y-4">
      <div>
        <h3 className="font-semibold text-lg mb-1">IVR Nodes</h3>
        <p className="text-xs text-gray-500">Click to add nodes to the flow</p>
      </div>

      <div className="space-y-2">
        {nodeDefinitions.map((nodeDef) => {
          const Icon = nodeDef.icon;
          return (
            <button
              key={nodeDef.type}
              onClick={() => onAddNode(nodeDef.type)}
              className={`w-full p-3 rounded-lg border-2 text-left transition-colors ${nodeDef.color}`}
            >
              <div className="flex items-start gap-2">
                <Icon size={18} className="mt-0.5 flex-shrink-0" />
                <div>
                  <div className="font-medium text-sm">{nodeDef.label}</div>
                  <div className="text-xs text-gray-600">{nodeDef.description}</div>
                </div>
              </div>
            </button>
          );
        })}
      </div>

      <div className="pt-4 border-t">
        <div className="text-xs text-gray-500 space-y-1">
          <p className="font-medium">Tips:</p>
          <ul className="list-disc list-inside space-y-1">
            <li>Every flow starts with a Start node</li>
            <li>Connect nodes by dragging from the bottom circle to the top circle</li>
            <li>Click a node to configure it</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
