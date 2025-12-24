import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation } from '@tanstack/react-query';
import { ArrowLeft, Save } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { IVRFlowBuilderWithProvider } from '@/components/ivr/IVRFlowBuilder';
import { ivrService } from '@/services/ivrService';
import { useToast } from '@/hooks/use-toast';
import { Node, Edge, Viewport } from 'reactflow';
import type { IVRNode } from '@/types/ivr';

export function IVRBuilderPage() {
  const { flowId } = useParams<{ flowId: string }>();
  const navigate = useNavigate();
  const { toast } = useToast();
  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [viewport, setViewport] = useState<Viewport | undefined>();

  // Load flow data
  const { data: flow, isLoading } = useQuery({
    queryKey: ['ivr-flow', flowId],
    queryFn: () => flowId ? ivrService.getFlow(flowId) : null,
    enabled: !!flowId,
  });

  // Save mutation
  const saveMutation = useMutation({
    mutationFn: async ({
      nodes,
      edges,
      viewport,
    }: {
      nodes: Node[];
      edges: Edge[];
      viewport?: Viewport;
    }) => {
      if (!flowId) throw new Error('No flow ID');

      return await ivrService.createVersion(flowId, {
        definition: {
          nodes: nodes as IVRNode[],
          edges,
          start_node: nodes.find((n) => n.type === 'start')?.id,
        },
        viewport: viewport
          ? { x: viewport.x, y: viewport.y, zoom: viewport.zoom }
          : undefined,
      });
    },
    onSuccess: () => {
      toast({
        title: 'Flow saved',
        description: 'Your IVR flow has been saved successfully',
      });
    },
    onError: (error) => {
      toast({
        title: 'Error saving flow',
        description: error instanceof Error ? error.message : 'Failed to save flow',
        variant: 'destructive',
      });
    },
  });

  // Load flow definition when data is available
  useEffect(() => {
    if (flow && flow.versions && flow.versions.length > 0) {
      const latestVersion = flow.versions[0];
      if (latestVersion.definition) {
        setNodes(latestVersion.definition.nodes as Node[] || []);
        setEdges(latestVersion.definition.edges || []);
        if (latestVersion.viewport) {
          setViewport(latestVersion.viewport as Viewport);
        }
      }
    }
  }, [flow]);

  const handleSave = (nodes: Node[], edges: Edge[], viewport?: Viewport) => {
    saveMutation.mutate({ nodes, edges, viewport });
  };

  if (!flowId) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center space-y-4">
          <h2 className="text-2xl font-semibold">No flow selected</h2>
          <Button onClick={() => navigate('/ivr')}>Go to IVR Flows</Button>
        </div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-muted-foreground">Loading flow...</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)]">
      <div className="border-b bg-white px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => navigate('/ivr')}
          >
            <ArrowLeft size={20} />
          </Button>
          <div>
            <h1 className="text-xl font-semibold">{flow?.name || 'IVR Flow'}</h1>
            {flow?.description && (
              <p className="text-sm text-muted-foreground">{flow.description}</p>
            )}
          </div>
        </div>
        <div className="flex gap-2">
          <Button
            onClick={() => handleSave(nodes, edges, viewport)}
            disabled={saveMutation.isPending}
          >
            <Save size={16} className="mr-2" />
            {saveMutation.isPending ? 'Saving...' : 'Save Flow'}
          </Button>
        </div>
      </div>

      <div className="flex-1">
        <IVRFlowBuilderWithProvider
          flowId={flowId}
          initialNodes={nodes as IVRNode[]}
          initialEdges={edges}
          onSave={(nodes, edges) => handleSave(nodes, edges, viewport)}
        />
      </div>
    </div>
  );
}
