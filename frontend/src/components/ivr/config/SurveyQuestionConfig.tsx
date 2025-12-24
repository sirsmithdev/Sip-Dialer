import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { SurveyQuestionNodeData } from '@/types/ivr';

interface SurveyQuestionConfigProps {
  data: SurveyQuestionNodeData;
  onUpdate: (data: Record<string, unknown>) => void;
}

export function SurveyQuestionConfig({ data, onUpdate }: SurveyQuestionConfigProps) {
  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="question_id">Question ID</Label>
        <Input
          id="question_id"
          placeholder="e.g., satisfaction"
          value={data.question_id || ''}
          onChange={(e) => onUpdate({ question_id: e.target.value })}
        />
        <p className="text-xs text-gray-500">
          Unique identifier for this question
        </p>
      </div>

      <div className="space-y-2">
        <Label htmlFor="question_text">Question Text</Label>
        <Input
          id="question_text"
          placeholder="e.g., How satisfied are you?"
          value={data.question_text || ''}
          onChange={(e) => onUpdate({ question_text: e.target.value })}
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="prompt_audio">Prompt Audio</Label>
        <Input
          id="prompt_audio"
          placeholder="Select audio file..."
          value={data.prompt_audio_name || ''}
          onChange={(e) => onUpdate({ prompt_audio_name: e.target.value })}
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="valid_inputs">Valid Inputs (comma separated)</Label>
        <Input
          id="valid_inputs"
          placeholder="e.g., 1,2,3,4,5"
          value={data.valid_inputs?.join(',') || ''}
          onChange={(e) => onUpdate({ valid_inputs: e.target.value.split(',').map(v => v.trim()) })}
        />
        <p className="text-xs text-gray-500">
          Acceptable DTMF inputs for this question
        </p>
      </div>

      <div className="space-y-2">
        <Label htmlFor="timeout">Timeout (seconds)</Label>
        <Input
          id="timeout"
          type="number"
          min="1"
          max="60"
          value={data.timeout || 5}
          onChange={(e) => onUpdate({ timeout: parseInt(e.target.value) })}
        />
      </div>
    </div>
  );
}
