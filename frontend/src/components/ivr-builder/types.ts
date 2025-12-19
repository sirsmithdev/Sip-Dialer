import type { Edge } from '@xyflow/react';

// IVR Node Types matching backend enum
export type IVRNodeType =
  | 'start'
  | 'play_audio'
  | 'menu'
  | 'survey_question'
  | 'record'
  | 'transfer'
  | 'conditional'
  | 'set_variable'
  | 'hangup';

// Node data interfaces - using index signature for React Flow compatibility
export interface BaseNodeData {
  [key: string]: unknown;
  label: string;
  type: IVRNodeType;
  description?: string;
}

export interface StartNodeData extends BaseNodeData {
  type: 'start';
}

export interface PlayAudioNodeData extends BaseNodeData {
  type: 'play_audio';
  audioFileId?: string;
  audioFileName?: string;
  waitForDtmf?: boolean;
}

export interface MenuNodeData extends BaseNodeData {
  type: 'menu';
  promptAudioId?: string;
  promptAudioName?: string;
  timeout?: number;
  maxRetries?: number;
  options: Record<string, string>;
}

export interface SurveyQuestionNodeData extends BaseNodeData {
  type: 'survey_question';
  questionId?: string;
  promptAudioId?: string;
  promptAudioName?: string;
  validInputs?: string[];
}

export interface RecordNodeData extends BaseNodeData {
  type: 'record';
  maxDuration?: number;
  beep?: boolean;
  silenceTimeout?: number;
}

export interface TransferNodeData extends BaseNodeData {
  type: 'transfer';
  destination?: string;
  transferType?: 'blind' | 'attended';
}

export interface ConditionalNodeData extends BaseNodeData {
  type: 'conditional';
  variable?: string;
  operator?: 'equals' | 'not_equals' | 'greater' | 'less' | 'contains';
  value?: string;
}

export interface SetVariableNodeData extends BaseNodeData {
  type: 'set_variable';
  variableName?: string;
  value?: string;
}

export interface HangupNodeData extends BaseNodeData {
  type: 'hangup';
  reason?: string;
}

export type IVRNodeData =
  | StartNodeData
  | PlayAudioNodeData
  | MenuNodeData
  | SurveyQuestionNodeData
  | RecordNodeData
  | TransferNodeData
  | ConditionalNodeData
  | SetVariableNodeData
  | HangupNodeData;

// Custom IVR Node type (simplified for React Flow compatibility)
export interface IVRNode {
  id: string;
  type: IVRNodeType;
  position: { x: number; y: number };
  data: IVRNodeData;
}

export type IVREdge = Edge;

// Flow definition matching backend structure
export interface IVRFlowDefinition {
  nodes: IVRNode[];
  edges: IVREdge[];
  startNode?: string;
}

export interface IVRFlow {
  id: string;
  name: string;
  description?: string;
  status: 'draft' | 'published' | 'archived';
  activeVersionId?: string;
  createdAt: string;
  updatedAt: string;
}

export interface IVRFlowVersion {
  id: string;
  flowId: string;
  version: number;
  definition: IVRFlowDefinition;
  viewport?: { x: number; y: number; zoom: number };
  notes?: string;
  createdAt: string;
}

// Node configuration for the toolbar
export interface NodeConfig {
  type: IVRNodeType;
  label: string;
  description: string;
  icon: string;
  color: string;
  defaultData: IVRNodeData;
}

export const NODE_CONFIGS: NodeConfig[] = [
  {
    type: 'start',
    label: 'Start',
    description: 'Entry point of the IVR flow',
    icon: 'Play',
    color: 'bg-green-500',
    defaultData: { label: 'Start', type: 'start' },
  },
  {
    type: 'play_audio',
    label: 'Play Audio',
    description: 'Play an audio file to the caller',
    icon: 'Volume2',
    color: 'bg-blue-500',
    defaultData: { label: 'Play Audio', type: 'play_audio', waitForDtmf: false },
  },
  {
    type: 'menu',
    label: 'Menu',
    description: 'Present options and route based on input',
    icon: 'List',
    color: 'bg-purple-500',
    defaultData: { label: 'Menu', type: 'menu', timeout: 5, maxRetries: 3, options: {} },
  },
  {
    type: 'survey_question',
    label: 'Survey Question',
    description: 'Ask a survey question and record response',
    icon: 'HelpCircle',
    color: 'bg-orange-500',
    defaultData: { label: 'Survey Question', type: 'survey_question', questionId: '', validInputs: ['1', '2', '3', '4', '5'] },
  },
  {
    type: 'record',
    label: 'Record',
    description: 'Record caller voice message',
    icon: 'Mic',
    color: 'bg-red-500',
    defaultData: { label: 'Record', type: 'record', maxDuration: 60, beep: true, silenceTimeout: 3 },
  },
  {
    type: 'transfer',
    label: 'Transfer',
    description: 'Transfer call to another destination',
    icon: 'PhoneForwarded',
    color: 'bg-cyan-500',
    defaultData: { label: 'Transfer', type: 'transfer', destination: '', transferType: 'blind' },
  },
  {
    type: 'conditional',
    label: 'Condition',
    description: 'Branch based on a condition',
    icon: 'GitBranch',
    color: 'bg-yellow-500',
    defaultData: { label: 'Condition', type: 'conditional', variable: '', operator: 'equals', value: '' },
  },
  {
    type: 'set_variable',
    label: 'Set Variable',
    description: 'Set a variable value',
    icon: 'Variable',
    color: 'bg-indigo-500',
    defaultData: { label: 'Set Variable', type: 'set_variable', variableName: '', value: '' },
  },
  {
    type: 'hangup',
    label: 'Hangup',
    description: 'End the call',
    icon: 'PhoneOff',
    color: 'bg-gray-500',
    defaultData: { label: 'Hangup', type: 'hangup' },
  },
];
