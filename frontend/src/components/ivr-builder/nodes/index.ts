import { BaseNode } from './BaseNode';
import type { IVRNodeType } from '../types';

// All node types use the same BaseNode component
// The styling and behavior is determined by the data.type property
export const nodeTypes: Record<IVRNodeType, typeof BaseNode> = {
  start: BaseNode,
  play_audio: BaseNode,
  menu: BaseNode,
  survey_question: BaseNode,
  record: BaseNode,
  transfer: BaseNode,
  conditional: BaseNode,
  set_variable: BaseNode,
  hangup: BaseNode,
};

export { BaseNode };
