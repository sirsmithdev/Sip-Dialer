import { useCallback, useRef, useState } from 'react';
import {
  ReactFlow,
  Controls,
  Background,
  MiniMap,
  addEdge,
  useNodesState,
  useEdgesState,
  type Connection,
  type Edge,
  type Node,
  BackgroundVariant,
  type ReactFlowInstance,
  Panel,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import { nodeTypes } from './nodes';
import { NodeToolbar } from './NodeToolbar';
import { NodeConfigPanel } from './NodeConfigPanel';
import type { IVRNode, IVRNodeData, NodeConfig } from './types';
import { Button } from '@/components/ui/button';
import { Save, Undo, Redo, ZoomIn, ZoomOut, Maximize } from 'lucide-react';

// Initial nodes with a start node
const initialNodes: Node[] = [
  {
    id: 'start-1',
    type: 'start',
    position: { x: 250, y: 50 },
    data: { label: 'Start', type: 'start' },
  },
];

const initialEdges: Edge[] = [];

interface IVRCanvasProps {
  flowId?: string;
  onSave?: (nodes: IVRNode[], edges: Edge[]) => void;
}

export function IVRCanvas({ onSave }: IVRCanvasProps) {
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  const [reactFlowInstance, setReactFlowInstance] = useState<ReactFlowInstance | null>(null);
  const [selectedNode, setSelectedNode] = useState<IVRNode | null>(null);

  // Handle new connections
  const onConnect = useCallback(
    (params: Connection) => {
      const newEdge = {
        ...params,
        type: 'smoothstep',
        animated: true,
        style: { stroke: 'hsl(var(--primary))', strokeWidth: 2 },
      };
      setEdges((eds) => addEdge(newEdge, eds));
    },
    [setEdges]
  );

  // Handle node selection
  const onNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      setSelectedNode(node as unknown as IVRNode);
    },
    []
  );

  // Handle canvas click (deselect)
  const onPaneClick = useCallback(() => {
    setSelectedNode(null);
  }, []);

  // Handle drag over for dropping new nodes
  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  // Handle dropping new nodes
  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();

      const nodeConfigJson = event.dataTransfer.getData('application/ivr-node');
      if (!nodeConfigJson || !reactFlowInstance || !reactFlowWrapper.current) return;

      const nodeConfig: NodeConfig = JSON.parse(nodeConfigJson);

      // Check if trying to add multiple start nodes
      if (nodeConfig.type === 'start' && nodes.some(n => (n.data as IVRNodeData).type === 'start')) {
        return; // Don't allow multiple start nodes
      }

      const bounds = reactFlowWrapper.current.getBoundingClientRect();
      const position = reactFlowInstance.screenToFlowPosition({
        x: event.clientX - bounds.left,
        y: event.clientY - bounds.top,
      });

      const newNode: Node = {
        id: `${nodeConfig.type}-${Date.now()}`,
        type: nodeConfig.type,
        position,
        data: {
          ...nodeConfig.defaultData,
          label: nodeConfig.label,
        },
      };

      setNodes((nds) => [...nds, newNode]);
    },
    [reactFlowInstance, nodes, setNodes]
  );

  // Handle drag start from toolbar
  const onDragStart = useCallback((event: React.DragEvent, nodeConfig: NodeConfig) => {
    event.dataTransfer.setData('application/ivr-node', JSON.stringify(nodeConfig));
    event.dataTransfer.effectAllowed = 'move';
  }, []);

  // Update node data
  const onUpdateNode = useCallback(
    (nodeId: string, data: Partial<IVRNodeData>) => {
      setNodes((nds) =>
        nds.map((node) => {
          if (node.id === nodeId) {
            return {
              ...node,
              data: { ...node.data, ...data },
            };
          }
          return node;
        })
      );
      // Update selected node state
      setSelectedNode((prev) => {
        if (prev && prev.id === nodeId) {
          return { ...prev, data: { ...prev.data, ...data } as IVRNodeData };
        }
        return prev;
      });
    },
    [setNodes]
  );

  // Delete node
  const onDeleteNode = useCallback(
    (nodeId: string) => {
      setNodes((nds) => nds.filter((node) => node.id !== nodeId));
      setEdges((eds) => eds.filter((edge) => edge.source !== nodeId && edge.target !== nodeId));
      setSelectedNode(null);
    },
    [setNodes, setEdges]
  );

  // Save flow
  const handleSave = useCallback(() => {
    if (onSave) {
      const ivrNodes = nodes.map(n => ({
        id: n.id,
        type: n.type as IVRNode['type'],
        position: n.position,
        data: n.data as IVRNodeData,
      }));
      onSave(ivrNodes, edges);
    }
  }, [nodes, edges, onSave]);

  // Fit view
  const handleFitView = useCallback(() => {
    reactFlowInstance?.fitView({ padding: 0.2 });
  }, [reactFlowInstance]);

  return (
    <div className="flex h-full bg-background">
      {/* Left Toolbar */}
      <NodeToolbar onDragStart={onDragStart} />

      {/* Canvas */}
      <div className="flex-1 h-full" ref={reactFlowWrapper}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onNodeClick={onNodeClick}
          onPaneClick={onPaneClick}
          onDrop={onDrop}
          onDragOver={onDragOver}
          onInit={setReactFlowInstance}
          nodeTypes={nodeTypes}
          fitView
          snapToGrid
          snapGrid={[15, 15]}
          defaultEdgeOptions={{
            type: 'smoothstep',
            animated: true,
            style: { stroke: 'hsl(var(--primary))', strokeWidth: 2 },
          }}
          className="bg-muted/30"
        >
          <Background variant={BackgroundVariant.Dots} gap={20} size={1} color="hsl(var(--muted-foreground) / 0.2)" />
          <MiniMap
            nodeColor={(node) => {
              const type = (node.data as IVRNodeData).type;
              const colors: Record<string, string> = {
                start: '#22c55e',
                play_audio: '#3b82f6',
                menu: '#a855f7',
                survey_question: '#f97316',
                record: '#ef4444',
                transfer: '#06b6d4',
                conditional: '#eab308',
                set_variable: '#6366f1',
                hangup: '#6b7280',
              };
              return colors[type] || '#6b7280';
            }}
            maskColor="rgba(0, 0, 0, 0.1)"
            className="!bg-card !border !border-border !rounded-lg"
          />
          <Controls
            showZoom={false}
            showFitView={false}
            showInteractive={false}
            className="!bg-card !border !border-border !rounded-lg !shadow-lg"
          />

          {/* Top Panel with Actions */}
          <Panel position="top-right" className="flex gap-2">
            <Button variant="outline" size="sm" onClick={() => reactFlowInstance?.zoomIn()}>
              <ZoomIn className="w-4 h-4" />
            </Button>
            <Button variant="outline" size="sm" onClick={() => reactFlowInstance?.zoomOut()}>
              <ZoomOut className="w-4 h-4" />
            </Button>
            <Button variant="outline" size="sm" onClick={handleFitView}>
              <Maximize className="w-4 h-4" />
            </Button>
            <div className="w-px bg-border mx-1" />
            <Button variant="outline" size="sm" disabled>
              <Undo className="w-4 h-4" />
            </Button>
            <Button variant="outline" size="sm" disabled>
              <Redo className="w-4 h-4" />
            </Button>
            <div className="w-px bg-border mx-1" />
            <Button size="sm" className="gradient-primary" onClick={handleSave}>
              <Save className="w-4 h-4 mr-2" />
              Save Flow
            </Button>
          </Panel>

          {/* Bottom Panel with Stats */}
          <Panel position="bottom-left" className="!bg-card !border !border-border !rounded-lg !px-3 !py-2">
            <p className="text-xs text-muted-foreground">
              {nodes.length} nodes • {edges.length} connections
            </p>
          </Panel>
        </ReactFlow>
      </div>

      {/* Right Config Panel */}
      {selectedNode && (
        <NodeConfigPanel
          node={selectedNode}
          onClose={() => setSelectedNode(null)}
          onUpdate={onUpdateNode}
          onDelete={onDeleteNode}
        />
      )}
    </div>
  );
}
