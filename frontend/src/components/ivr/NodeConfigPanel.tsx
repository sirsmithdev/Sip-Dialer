import { Node } from 'reactflow';
import { X, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { PlayAudioConfig } from './config/PlayAudioConfig';
import { MenuConfig } from './config/MenuConfig';
import { SurveyQuestionConfig } from './config/SurveyQuestionConfig';
import { RecordConfig } from './config/RecordConfig';
import { TransferConfig } from './config/TransferConfig';
import { ConditionalConfig } from './config/ConditionalConfig';
import { SetVariableConfig } from './config/SetVariableConfig';
import { HangupConfig } from './config/HangupConfig';

interface NodeConfigPanelProps {
  node: Node;
  onUpdate: (nodeId: string, data: Record<string, unknown>) => void;
  onDelete: (nodeId: string) => void;
  onClose: () => void;
}

export function NodeConfigPanel({ node, onUpdate, onDelete, onClose }: NodeConfigPanelProps) {
  const handleUpdate = (data: Record<string, unknown>) => {
    onUpdate(node.id, data);
  };

  const handleDelete = () => {
    if (confirm('Are you sure you want to delete this node?')) {
      onDelete(node.id);
    }
  };

  const renderConfig = () => {
    switch (node.type) {
      case 'start':
        return (
          <div className="text-sm text-gray-500">
            This is the starting point of your IVR flow. All flows begin here.
          </div>
        );
      case 'play_audio':
        return <PlayAudioConfig data={node.data} onUpdate={handleUpdate} />;
      case 'menu':
        return <MenuConfig data={node.data} onUpdate={handleUpdate} />;
      case 'survey_question':
        return <SurveyQuestionConfig data={node.data} onUpdate={handleUpdate} />;
      case 'record':
        return <RecordConfig data={node.data} onUpdate={handleUpdate} />;
      case 'transfer':
        return <TransferConfig data={node.data} onUpdate={handleUpdate} />;
      case 'conditional':
        return <ConditionalConfig data={node.data} onUpdate={handleUpdate} />;
      case 'set_variable':
        return <SetVariableConfig data={node.data} onUpdate={handleUpdate} />;
      case 'hangup':
        return <HangupConfig data={node.data} onUpdate={handleUpdate} />;
      default:
        return <div className="text-sm text-gray-500">No configuration available</div>;
    }
  };

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="p-4 border-b flex items-center justify-between">
        <div>
          <h3 className="font-semibold text-lg">Node Configuration</h3>
          <p className="text-sm text-gray-500 capitalize">{node.type?.replace('_', ' ')}</p>
        </div>
        <Button variant="ghost" size="icon" onClick={onClose}>
          <X size={20} />
        </Button>
      </div>

      {/* Configuration Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {renderConfig()}
      </div>

      {/* Footer Actions */}
      {node.type !== 'start' && (
        <>
          <Separator />
          <div className="p-4">
            <Button
              variant="destructive"
              className="w-full"
              onClick={handleDelete}
            >
              <Trash2 size={16} className="mr-2" />
              Delete Node
            </Button>
          </div>
        </>
      )}
    </div>
  );
}
