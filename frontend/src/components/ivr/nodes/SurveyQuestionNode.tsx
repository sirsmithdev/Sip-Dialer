import { memo } from 'react';
import { NodeProps } from 'reactflow';
import { MessageSquareQuote } from 'lucide-react';
import { BaseNode } from './BaseNode';
import { SurveyQuestionNodeData } from '@/types/ivr';

export const SurveyQuestionNode = memo(({ data, selected }: NodeProps<SurveyQuestionNodeData>) => {
  return (
    <BaseNode
      title="Survey Question"
      icon={<MessageSquareQuote size={16} />}
      selected={selected}
      color="bg-indigo-600"
    >
      <div className="space-y-1">
        {data.question_text ? (
          <p className="font-medium text-xs">{data.question_text}</p>
        ) : (
          <p className="text-gray-400 italic text-xs">No question text</p>
        )}
        {data.valid_inputs && data.valid_inputs.length > 0 && (
          <p className="text-xs text-gray-500">
            Valid inputs: {data.valid_inputs.join(', ')}
          </p>
        )}
      </div>
    </BaseNode>
  );
});

SurveyQuestionNode.displayName = 'SurveyQuestionNode';
