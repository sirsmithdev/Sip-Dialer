import { memo } from 'react';
import { X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import type { IVRNode, IVRNodeData } from './types';

interface NodeConfigPanelProps {
  node: IVRNode | null;
  onClose: () => void;
  onUpdate: (nodeId: string, data: Partial<IVRNodeData>) => void;
  onDelete: (nodeId: string) => void;
}

function NodeConfigPanelComponent({ node, onClose, onUpdate, onDelete }: NodeConfigPanelProps) {
  if (!node) return null;

  const data = node.data;

  const handleChange = (field: string, value: unknown) => {
    onUpdate(node.id, { [field]: value } as Partial<IVRNodeData>);
  };

  return (
    <div className="w-80 bg-card border-l border-border flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-border">
        <div>
          <h3 className="font-semibold text-sm">Configure Node</h3>
          <p className="text-xs text-muted-foreground capitalize">
            {data.type.replace('_', ' ')}
          </p>
        </div>
        <Button variant="ghost" size="icon" onClick={onClose}>
          <X className="w-4 h-4" />
        </Button>
      </div>

      {/* Config Form */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Common Fields */}
        <div className="space-y-2">
          <Label htmlFor="label">Label</Label>
          <Input
            id="label"
            value={data.label}
            onChange={(e) => handleChange('label', e.target.value)}
            placeholder="Node label"
          />
        </div>

        {/* Type-specific fields */}
        {data.type === 'play_audio' && (
          <>
            <div className="space-y-2">
              <Label htmlFor="audioFile">Audio File</Label>
              <Select
                value={data.audioFileId || ''}
                onValueChange={(v) => handleChange('audioFileId', v)}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select audio file" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="demo-welcome">Welcome Message</SelectItem>
                  <SelectItem value="demo-menu">Menu Prompt</SelectItem>
                  <SelectItem value="demo-goodbye">Goodbye</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="flex items-center justify-between">
              <Label htmlFor="waitForDtmf">Wait for DTMF</Label>
              <Switch
                id="waitForDtmf"
                checked={data.waitForDtmf || false}
                onCheckedChange={(v) => handleChange('waitForDtmf', v)}
              />
            </div>
          </>
        )}

        {data.type === 'menu' && (
          <>
            <div className="space-y-2">
              <Label htmlFor="timeout">Timeout (seconds)</Label>
              <Input
                id="timeout"
                type="number"
                min={1}
                max={30}
                value={data.timeout || 5}
                onChange={(e) => handleChange('timeout', parseInt(e.target.value))}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="maxRetries">Max Retries</Label>
              <Input
                id="maxRetries"
                type="number"
                min={0}
                max={10}
                value={data.maxRetries || 3}
                onChange={(e) => handleChange('maxRetries', parseInt(e.target.value))}
              />
            </div>
            <div className="space-y-2">
              <Label>Menu Options</Label>
              <p className="text-xs text-muted-foreground">
                Connect this node to other nodes to define menu options.
                Each connection represents a DTMF digit option.
              </p>
            </div>
          </>
        )}

        {data.type === 'survey_question' && (
          <>
            <div className="space-y-2">
              <Label htmlFor="questionId">Question ID</Label>
              <Input
                id="questionId"
                value={data.questionId || ''}
                onChange={(e) => handleChange('questionId', e.target.value)}
                placeholder="e.g., satisfaction"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="validInputs">Valid Inputs</Label>
              <Input
                id="validInputs"
                value={(data.validInputs || []).join(', ')}
                onChange={(e) => handleChange('validInputs', e.target.value.split(',').map(s => s.trim()))}
                placeholder="1, 2, 3, 4, 5"
              />
              <p className="text-xs text-muted-foreground">
                Comma-separated list of valid DTMF inputs
              </p>
            </div>
          </>
        )}

        {data.type === 'record' && (
          <>
            <div className="space-y-2">
              <Label htmlFor="maxDuration">Max Duration (seconds)</Label>
              <Input
                id="maxDuration"
                type="number"
                min={5}
                max={300}
                value={data.maxDuration || 60}
                onChange={(e) => handleChange('maxDuration', parseInt(e.target.value))}
              />
            </div>
            <div className="flex items-center justify-between">
              <Label htmlFor="beep">Play Beep</Label>
              <Switch
                id="beep"
                checked={data.beep !== false}
                onCheckedChange={(v) => handleChange('beep', v)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="silenceTimeout">Silence Timeout (seconds)</Label>
              <Input
                id="silenceTimeout"
                type="number"
                min={1}
                max={30}
                value={data.silenceTimeout || 3}
                onChange={(e) => handleChange('silenceTimeout', parseInt(e.target.value))}
              />
            </div>
          </>
        )}

        {data.type === 'transfer' && (
          <>
            <div className="space-y-2">
              <Label htmlFor="destination">Destination</Label>
              <Input
                id="destination"
                value={data.destination || ''}
                onChange={(e) => handleChange('destination', e.target.value)}
                placeholder="Extension or phone number"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="transferType">Transfer Type</Label>
              <Select
                value={data.transferType || 'blind'}
                onValueChange={(v) => handleChange('transferType', v)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="blind">Blind Transfer</SelectItem>
                  <SelectItem value="attended">Attended Transfer</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </>
        )}

        {data.type === 'conditional' && (
          <>
            <div className="space-y-2">
              <Label htmlFor="variable">Variable</Label>
              <Input
                id="variable"
                value={data.variable || ''}
                onChange={(e) => handleChange('variable', e.target.value)}
                placeholder="e.g., caller_input"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="operator">Operator</Label>
              <Select
                value={data.operator || 'equals'}
                onValueChange={(v) => handleChange('operator', v)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="equals">Equals</SelectItem>
                  <SelectItem value="not_equals">Not Equals</SelectItem>
                  <SelectItem value="greater">Greater Than</SelectItem>
                  <SelectItem value="less">Less Than</SelectItem>
                  <SelectItem value="contains">Contains</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="value">Value</Label>
              <Input
                id="value"
                value={data.value || ''}
                onChange={(e) => handleChange('value', e.target.value)}
                placeholder="Comparison value"
              />
            </div>
          </>
        )}

        {data.type === 'set_variable' && (
          <>
            <div className="space-y-2">
              <Label htmlFor="variableName">Variable Name</Label>
              <Input
                id="variableName"
                value={data.variableName || ''}
                onChange={(e) => handleChange('variableName', e.target.value)}
                placeholder="e.g., survey_response"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="value">Value</Label>
              <Input
                id="value"
                value={data.value || ''}
                onChange={(e) => handleChange('value', e.target.value)}
                placeholder="Value to set"
              />
            </div>
          </>
        )}

        {data.type === 'hangup' && (
          <div className="space-y-2">
            <Label htmlFor="reason">Reason (optional)</Label>
            <Input
              id="reason"
              value={data.reason || ''}
              onChange={(e) => handleChange('reason', e.target.value)}
              placeholder="e.g., survey_complete"
            />
          </div>
        )}

        {data.type === 'opt_out' && (
          <>
            <div className="p-3 bg-rose-500/10 border border-rose-500/20 rounded-md">
              <p className="text-xs text-rose-600 dark:text-rose-400">
                This node will add the caller's phone number to the Do-Not-Call (DNC) list.
                They will not receive future calls from this organization.
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="confirmationAudio">Confirmation Audio (optional)</Label>
              <Select
                value={data.confirmationAudioId || ''}
                onValueChange={(v) => handleChange('confirmationAudioId', v)}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select audio file" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">None</SelectItem>
                  <SelectItem value="demo-optout-confirm">Opt-out Confirmation</SelectItem>
                  <SelectItem value="demo-goodbye">Goodbye</SelectItem>
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                Audio to play after opt-out is recorded
              </p>
            </div>
            <div className="flex items-center justify-between">
              <Label htmlFor="hangupAfter">Hang up after opt-out</Label>
              <Switch
                id="hangupAfter"
                checked={data.hangupAfter !== false}
                onCheckedChange={(v) => handleChange('hangupAfter', v)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="reason">DNC Reason</Label>
              <Input
                id="reason"
                value={data.reason || ''}
                onChange={(e) => handleChange('reason', e.target.value)}
                placeholder="User requested removal"
              />
              <p className="text-xs text-muted-foreground">
                Reason stored in DNC entry for reference
              </p>
            </div>
          </>
        )}
      </div>

      {/* Footer */}
      <div className="p-4 border-t border-border">
        <Button
          variant="destructive"
          size="sm"
          className="w-full"
          onClick={() => onDelete(node.id)}
          disabled={data.type === 'start'}
        >
          Delete Node
        </Button>
        {data.type === 'start' && (
          <p className="text-xs text-muted-foreground text-center mt-2">
            Start node cannot be deleted
          </p>
        )}
      </div>
    </div>
  );
}

export const NodeConfigPanel = memo(NodeConfigPanelComponent);
