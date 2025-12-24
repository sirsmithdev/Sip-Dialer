// IVR Flow Builder types
import { Node, Edge } from 'reactflow';

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

export type IVRFlowStatus = 'draft' | 'published' | 'archived';

// Base node data interface
export interface BaseNodeData {
  label?: string;
}

// Specific node data types
export interface PlayAudioNodeData extends BaseNodeData {
  audio_file_id?: string;
  audio_file_name?: string;
  wait_for_dtmf?: boolean;
}

export interface MenuNodeData extends BaseNodeData {
  prompt_audio_id?: string;
  prompt_audio_name?: string;
  timeout?: number;
  max_retries?: number;
  options?: Record<string, string>; // key -> target node id
  invalid_input_audio_id?: string;
}

export interface SurveyQuestionNodeData extends BaseNodeData {
  question_id?: string;
  question_text?: string;
  prompt_audio_id?: string;
  prompt_audio_name?: string;
  valid_inputs?: string[];
  timeout?: number;
  max_retries?: number;
}

export interface RecordNodeData extends BaseNodeData {
  max_duration_seconds?: number;
  beep_before_recording?: boolean;
  finish_on_key?: string;
  timeout_seconds?: number;
}

export interface TransferNodeData extends BaseNodeData {
  destination_number?: string;
  timeout_seconds?: number;
  caller_id?: string;
}

export interface ConditionalNodeData extends BaseNodeData {
  variable_name?: string;
  operator?: 'equals' | 'not_equals' | 'greater_than' | 'less_than' | 'contains';
  value?: string;
  true_target?: string;
  false_target?: string;
}

export interface SetVariableNodeData extends BaseNodeData {
  variable_name?: string;
  value?: string;
  value_type?: 'static' | 'dtmf_input' | 'call_variable';
}

export interface HangupNodeData extends BaseNodeData {
  reason?: string;
}

export type IVRNodeData =
  | BaseNodeData
  | PlayAudioNodeData
  | MenuNodeData
  | SurveyQuestionNodeData
  | RecordNodeData
  | TransferNodeData
  | ConditionalNodeData
  | SetVariableNodeData
  | HangupNodeData;

// React Flow node with IVR data
export interface IVRNode extends Node {
  type: IVRNodeType;
  data: IVRNodeData;
}

// Flow definition
export interface IVRFlowDefinition {
  nodes: IVRNode[];
  edges: Edge[];
  start_node?: string;
}

// Flow version
export interface IVRFlowVersion {
  id: string;
  flow_id: string;
  version: number;
  definition: IVRFlowDefinition;
  viewport?: {
    x: number;
    y: number;
    zoom: number;
  };
  notes?: string;
  created_by_id?: string;
  created_at: string;
}

// Complete flow
export interface IVRFlow {
  id: string;
  name: string;
  description?: string;
  organization_id: string;
  status: IVRFlowStatus;
  active_version_id?: string;
  created_by_id?: string;
  created_at: string;
  updated_at: string;
  versions?: IVRFlowVersion[];
}

// API request/response types
export interface IVRFlowCreate {
  name: string;
  description?: string;
}

export interface IVRFlowUpdate {
  name?: string;
  description?: string;
  status?: IVRFlowStatus;
}

export interface IVRFlowVersionCreate {
  definition: IVRFlowDefinition;
  viewport?: {
    x: number;
    y: number;
    zoom: number;
  };
  notes?: string;
}

export interface IVRFlowListResponse {
  items: IVRFlow[];
  total: number;
  page: number;
  page_size: number;
}
