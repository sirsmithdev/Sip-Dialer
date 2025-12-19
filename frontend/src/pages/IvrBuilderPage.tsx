import { useState, useCallback } from 'react';
import { ReactFlowProvider } from '@xyflow/react';
import { Plus, FolderOpen, MoreVertical, GitBranch, Clock, Edit, Trash2, Copy } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { IVRCanvas } from '@/components/ivr-builder';
import type { IVRNode, IVREdge, IVRFlow } from '@/components/ivr-builder/types';
import { useToast } from '@/hooks/use-toast';

// Demo flows for display
const demoFlows: IVRFlow[] = [
  {
    id: '1',
    name: 'Customer Survey',
    description: 'Post-call satisfaction survey',
    status: 'published',
    createdAt: '2024-01-15T10:00:00Z',
    updatedAt: '2024-01-20T15:30:00Z',
  },
  {
    id: '2',
    name: 'Main Menu',
    description: 'Primary IVR menu for incoming calls',
    status: 'draft',
    createdAt: '2024-01-10T08:00:00Z',
    updatedAt: '2024-01-18T12:00:00Z',
  },
];

type ViewMode = 'list' | 'editor';

export function IvrBuilderPage() {
  const [viewMode, setViewMode] = useState<ViewMode>('list');
  const [flows, setFlows] = useState<IVRFlow[]>(demoFlows);
  const [selectedFlow, setSelectedFlow] = useState<IVRFlow | null>(null);
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [newFlowName, setNewFlowName] = useState('');
  const [newFlowDescription, setNewFlowDescription] = useState('');
  const { toast } = useToast();

  // Create new flow
  const handleCreateFlow = useCallback(() => {
    if (!newFlowName.trim()) return;

    const newFlow: IVRFlow = {
      id: `flow-${Date.now()}`,
      name: newFlowName.trim(),
      description: newFlowDescription.trim() || undefined,
      status: 'draft',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };

    setFlows((prev) => [newFlow, ...prev]);
    setSelectedFlow(newFlow);
    setViewMode('editor');
    setIsCreateDialogOpen(false);
    setNewFlowName('');
    setNewFlowDescription('');

    toast({
      title: 'Flow created',
      description: `"${newFlow.name}" has been created successfully.`,
    });
  }, [newFlowName, newFlowDescription, toast]);

  // Open flow for editing
  const handleOpenFlow = useCallback((flow: IVRFlow) => {
    setSelectedFlow(flow);
    setViewMode('editor');
  }, []);

  // Save flow
  const handleSaveFlow = useCallback(
    (nodes: IVRNode[], edges: IVREdge[]) => {
      console.log('Saving flow:', { nodes, edges });
      toast({
        title: 'Flow saved',
        description: 'Your IVR flow has been saved successfully.',
      });
    },
    [toast]
  );

  // Delete flow
  const handleDeleteFlow = useCallback(
    (flowId: string) => {
      setFlows((prev) => prev.filter((f) => f.id !== flowId));
      toast({
        title: 'Flow deleted',
        description: 'The IVR flow has been deleted.',
      });
    },
    [toast]
  );

  // Duplicate flow
  const handleDuplicateFlow = useCallback(
    (flow: IVRFlow) => {
      const duplicatedFlow: IVRFlow = {
        ...flow,
        id: `flow-${Date.now()}`,
        name: `${flow.name} (Copy)`,
        status: 'draft',
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      };
      setFlows((prev) => [duplicatedFlow, ...prev]);
      toast({
        title: 'Flow duplicated',
        description: `"${duplicatedFlow.name}" has been created.`,
      });
    },
    [toast]
  );

  // Back to list
  const handleBackToList = useCallback(() => {
    setViewMode('list');
    setSelectedFlow(null);
  }, []);

  // Editor View
  if (viewMode === 'editor') {
    return (
      <div className="h-[calc(100vh-8rem)] flex flex-col -m-6">
        {/* Editor Header */}
        <div className="flex items-center justify-between px-6 py-3 border-b border-border bg-card">
          <div className="flex items-center gap-4">
            <Button variant="ghost" size="sm" onClick={handleBackToList}>
              ← Back to Flows
            </Button>
            <div className="h-6 w-px bg-border" />
            <div>
              <h2 className="font-semibold">{selectedFlow?.name || 'Untitled Flow'}</h2>
              <p className="text-xs text-muted-foreground">
                {selectedFlow?.description || 'No description'}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant={selectedFlow?.status === 'published' ? 'default' : 'secondary'}>
              {selectedFlow?.status || 'draft'}
            </Badge>
          </div>
        </div>

        {/* Canvas */}
        <div className="flex-1">
          <ReactFlowProvider>
            <IVRCanvas flowId={selectedFlow?.id} onSave={handleSaveFlow} />
          </ReactFlowProvider>
        </div>
      </div>
    );
  }

  // List View
  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">IVR Builder</h1>
          <p className="text-muted-foreground">
            Design interactive voice response flows for your campaigns
          </p>
        </div>
        <Button className="gradient-primary" onClick={() => setIsCreateDialogOpen(true)}>
          <Plus className="mr-2 h-4 w-4" />
          New Flow
        </Button>
      </div>

      {/* Flows Grid */}
      {flows.length > 0 ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {flows.map((flow) => (
            <Card key={flow.id} className="card-hover group">
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-purple-500/10 flex items-center justify-center">
                      <GitBranch className="w-5 h-5 text-purple-500" />
                    </div>
                    <div>
                      <CardTitle className="text-base">{flow.name}</CardTitle>
                      <Badge
                        variant={flow.status === 'published' ? 'default' : 'secondary'}
                        className="mt-1"
                      >
                        {flow.status}
                      </Badge>
                    </div>
                  </div>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="opacity-0 group-hover:opacity-100 transition-opacity"
                      >
                        <MoreVertical className="w-4 h-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem onClick={() => handleOpenFlow(flow)}>
                        <Edit className="w-4 h-4 mr-2" />
                        Edit
                      </DropdownMenuItem>
                      <DropdownMenuItem onClick={() => handleDuplicateFlow(flow)}>
                        <Copy className="w-4 h-4 mr-2" />
                        Duplicate
                      </DropdownMenuItem>
                      <DropdownMenuSeparator />
                      <DropdownMenuItem
                        className="text-destructive"
                        onClick={() => handleDeleteFlow(flow.id)}
                      >
                        <Trash2 className="w-4 h-4 mr-2" />
                        Delete
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground mb-4 line-clamp-2">
                  {flow.description || 'No description provided'}
                </p>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1 text-xs text-muted-foreground">
                    <Clock className="w-3 h-3" />
                    Updated {new Date(flow.updatedAt).toLocaleDateString()}
                  </div>
                  <Button size="sm" variant="outline" onClick={() => handleOpenFlow(flow)}>
                    <FolderOpen className="w-4 h-4 mr-2" />
                    Open
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <Card className="p-12">
          <div className="flex flex-col items-center justify-center text-center">
            <div className="w-16 h-16 rounded-full bg-purple-500/10 flex items-center justify-center mb-4">
              <GitBranch className="w-8 h-8 text-purple-500" />
            </div>
            <h3 className="text-lg font-semibold mb-2">No IVR flows yet</h3>
            <p className="text-muted-foreground mb-4 max-w-sm">
              Create your first IVR flow to design interactive voice response experiences for your
              callers.
            </p>
            <Button className="gradient-primary" onClick={() => setIsCreateDialogOpen(true)}>
              <Plus className="mr-2 h-4 w-4" />
              Create Your First Flow
            </Button>
          </div>
        </Card>
      )}

      {/* Create Flow Dialog */}
      <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create New IVR Flow</DialogTitle>
            <DialogDescription>
              Create a new IVR flow to design interactive voice experiences for your callers.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="name">Flow Name</Label>
              <Input
                id="name"
                value={newFlowName}
                onChange={(e) => setNewFlowName(e.target.value)}
                placeholder="e.g., Customer Survey"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="description">Description (optional)</Label>
              <Input
                id="description"
                value={newFlowDescription}
                onChange={(e) => setNewFlowDescription(e.target.value)}
                placeholder="Brief description of this flow"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsCreateDialogOpen(false)}>
              Cancel
            </Button>
            <Button className="gradient-primary" onClick={handleCreateFlow} disabled={!newFlowName.trim()}>
              Create Flow
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
