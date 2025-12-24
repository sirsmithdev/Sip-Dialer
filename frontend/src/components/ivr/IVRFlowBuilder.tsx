import { useCallback, useState } from 'react';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  addEdge,
  useNodesState,
  useEdgesState,
  Connection,
  Edge,
  Node,
  ReactFlowProvider,
  BackgroundVariant,
} from 'reactflow';
import 'reactflow/dist/style.css';

import {
  StartNode,
  PlayAudioNode,
  MenuNode,
  SurveyQuestionNode,
  RecordNode,
  TransferNode,
  ConditionalNode,
  SetVariableNode,
  HangupNode,
} from './nodes';
import { IVRNode, IVRNodeType } from '@/types/ivr';
import { NodePalette } from './NodePalette';
import { NodeConfigPanel } from './NodeConfigPanel';

const nodeTypes = {
  start: StartNode,
  play_audio: PlayAudioNode,
  menu: MenuNode,
  survey_question: SurveyQuestionNode,
  record: RecordNode,
  transfer: TransferNode,
  conditional: ConditionalNode,
  set_variable: SetVariableNode,
  hangup: HangupNode,
};

interface IVRFlowBuilderProps {
  flowId?: string;
  initialNodes?: IVRNode[];
  initialEdges?: Edge[];
  onSave?: (nodes: Node[], edges: Edge[]) => void;
}

let nodeIdCounter = 1;

export function IVRFlowBuilder({
  initialNodes = [],
  initialEdges = [],
  onSave,
}: IVRFlowBuilderProps) {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);

  // Add start node if no nodes exist
  useState(() => {
    if (initialNodes.length === 0) {
      const startNode: IVRNode = {
        id: 'start-1',
        type: 'start',
        position: { x: 250, y: 50 },
        data: { label: 'Start' },
      };
      setNodes([startNode]);
    }
  });

  const onConnect = useCallback(
    (params: Connection) => setEdges((eds) => addEdge(params, eds)),
    [setEdges]
  );

  const onNodeClick = useCallback((_event: React.MouseEvent, node: Node) => {
    setSelectedNode(node);
  }, []);

  const onPaneClick = useCallback(() => {
    setSelectedNode(null);
  }, []);

  const handleAddNode = useCallback(
    (type: IVRNodeType) => {
      const newNode: IVRNode = {
        id: `${type}-${nodeIdCounter++}`,
        type,
        position: {
          x: Math.random() * 400 + 100,
          y: Math.random() * 400 + 100,
        },
        data: { label: type.replace('_', ' ').toUpperCase() },
      };
      setNodes((nds) => [...nds, newNode]);
    },
    [setNodes]
  );

  const handleUpdateNode = useCallback(
    (nodeId: string, data: Record<string, unknown>) => {
      setNodes((nds) =>
        nds.map((node) =>
          node.id === nodeId ? { ...node, data: { ...node.data, ...data } } : node
        )
      );
    },
    [setNodes]
  );

  const handleDeleteNode = useCallback(
    (nodeId: string) => {
      setNodes((nds) => nds.filter((node) => node.id !== nodeId));
      setEdges((eds) => eds.filter((edge) => edge.source !== nodeId && edge.target !== nodeId));
      setSelectedNode(null);
    },
    [setNodes, setEdges]
  );

  const handleSave = useCallback(() => {
    if (onSave) {
      onSave(nodes, edges);
    }
  }, [nodes, edges, onSave]);

  const minimapNodeColor = useCallback((node: Node) => {
    switch (node.type) {
      case 'start':
        return '#16a34a';
      case 'play_audio':
        return '#9333ea';
      case 'menu':
        return '#2563eb';
      case 'survey_question':
        return '#4f46e5';
      case 'record':
        return '#dc2626';
      case 'transfer':
        return '#ea580c';
      case 'conditional':
        return '#ca8a04';
      case 'set_variable':
        return '#0d9488';
      case 'hangup':
        return '#4b5563';
      default:
        return '#6b7280';
    }
  }, []);

  return (
    <div className="flex h-full w-full">
      {/* Node Palette Sidebar */}
      <div className="w-64 border-r bg-white p-4">
        <NodePalette onAddNode={handleAddNode} />
      </div>

      {/* Flow Canvas */}
      <div className="flex-1 relative">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onNodeClick={onNodeClick}
          onPaneClick={onPaneClick}
          nodeTypes={nodeTypes}
          fitView
          attributionPosition="bottom-left"
        >
          <Background variant={BackgroundVariant.Dots} gap={12} size={1} />
          <Controls />
          <MiniMap
            nodeColor={minimapNodeColor}
            maskColor="rgba(0, 0, 0, 0.1)"
            style={{ width: 120, height: 80 }}
          />
        </ReactFlow>

        {/* Save Button */}
        <div className="absolute top-4 right-4 z-10">
          <button
            onClick={handleSave}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 shadow-lg"
          >
            Save Flow
          </button>
        </div>
      </div>

      {/* Node Configuration Panel */}
      {selectedNode && (
        <div className="w-80 border-l bg-white">
          <NodeConfigPanel
            node={selectedNode}
            onUpdate={handleUpdateNode}
            onDelete={handleDeleteNode}
            onClose={() => setSelectedNode(null)}
          />
        </div>
      )}
    </div>
  );
}

// Wrapper with ReactFlowProvider
export function IVRFlowBuilderWithProvider(props: IVRFlowBuilderProps) {
  return (
    <ReactFlowProvider>
      <IVRFlowBuilder {...props} />
    </ReactFlowProvider>
  );
}
