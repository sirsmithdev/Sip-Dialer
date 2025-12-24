import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Plus, Edit, Trash2, GitBranch, Clock, FileText } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { ivrService } from '@/services/ivrService';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { cn } from '@/lib/utils';

export function IVRFlowsPage() {
  const navigate = useNavigate();
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [newFlowName, setNewFlowName] = useState('');
  const [newFlowDescription, setNewFlowDescription] = useState('');
  const [creating, setCreating] = useState(false);

  const { data: flowsData, refetch } = useQuery({
    queryKey: ['ivr-flows'],
    queryFn: () => ivrService.listFlows(),
  });

  const handleCreateFlow = async () => {
    if (!newFlowName.trim()) return;

    setCreating(true);
    try {
      const newFlow = await ivrService.createFlow({
        name: newFlowName,
        description: newFlowDescription || undefined,
      });
      setCreateDialogOpen(false);
      setNewFlowName('');
      setNewFlowDescription('');
      navigate(`/ivr/${newFlow.id}`);
    } catch (error) {
      console.error('Failed to create flow:', error);
    } finally {
      setCreating(false);
    }
  };

  const handleDeleteFlow = async (flowId: string) => {
    if (!confirm('Are you sure you want to delete this flow?')) return;

    try {
      await ivrService.deleteFlow(flowId);
      refetch();
    } catch (error) {
      console.error('Failed to delete flow:', error);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="p-3 rounded-xl bg-gradient-to-br from-violet-500 to-purple-600 shadow-lg shadow-violet-500/25">
            <GitBranch className="h-6 w-6 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">IVR Flows</h1>
            <p className="text-gray-500">
              Manage your interactive voice response flows
            </p>
          </div>
        </div>
        <Button
          onClick={() => setCreateDialogOpen(true)}
          className="bg-gradient-to-r from-violet-600 to-purple-600 hover:from-violet-700 hover:to-purple-700 shadow-lg shadow-violet-500/25"
        >
          <Plus size={16} className="mr-2" />
          New Flow
        </Button>
      </div>

      {/* Flows Grid */}
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {flowsData?.items.map((flow) => (
          <Card
            key={flow.id}
            className="group border-0 shadow-lg shadow-gray-200/50 hover:shadow-xl transition-all duration-200 cursor-pointer overflow-hidden"
            onClick={() => navigate(`/ivr/${flow.id}`)}
          >
            <CardContent className="p-0">
              {/* Card Header with Gradient */}
              <div className="bg-gradient-to-br from-violet-500/10 to-purple-500/10 p-4 border-b border-gray-100">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-gradient-to-br from-violet-500 to-purple-600 shadow-md">
                      <GitBranch className="h-4 w-4 text-white" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-gray-900">{flow.name}</h3>
                      <span
                        className={cn(
                          'inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium mt-1',
                          flow.status === 'published'
                            ? 'bg-emerald-100 text-emerald-700'
                            : flow.status === 'draft'
                            ? 'bg-amber-100 text-amber-700'
                            : 'bg-gray-100 text-gray-600'
                        )}
                      >
                        {flow.status}
                      </span>
                    </div>
                  </div>
                  <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 hover:bg-violet-100 hover:text-violet-600"
                      onClick={(e) => {
                        e.stopPropagation();
                        navigate(`/ivr/${flow.id}`);
                      }}
                    >
                      <Edit size={14} />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 hover:bg-red-100 hover:text-red-600"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDeleteFlow(flow.id);
                      }}
                    >
                      <Trash2 size={14} />
                    </Button>
                  </div>
                </div>
              </div>

              {/* Card Body */}
              <div className="p-4">
                {flow.description ? (
                  <p className="text-sm text-gray-600 line-clamp-2 mb-3">
                    {flow.description}
                  </p>
                ) : (
                  <p className="text-sm text-gray-400 italic mb-3">
                    No description
                  </p>
                )}

                <div className="flex items-center gap-4 text-xs text-gray-500">
                  <span className="flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    Updated {new Date(flow.updated_at).toLocaleDateString()}
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Empty State */}
      {flowsData?.items.length === 0 && (
        <Card className="border-0 shadow-lg shadow-gray-200/50">
          <CardContent className="flex flex-col items-center justify-center py-16">
            <div className="p-4 rounded-full bg-gradient-to-br from-violet-100 to-purple-100 mb-4">
              <FileText className="h-10 w-10 text-violet-500" />
            </div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              No IVR Flows Yet
            </h3>
            <p className="text-gray-500 text-center max-w-md mb-6">
              Create your first IVR flow to design interactive voice menus for your campaigns.
            </p>
            <Button
              onClick={() => setCreateDialogOpen(true)}
              className="bg-gradient-to-r from-violet-600 to-purple-600 hover:from-violet-700 hover:to-purple-700"
            >
              <Plus size={16} className="mr-2" />
              Create Your First Flow
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Create Dialog */}
      <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="text-xl font-semibold">Create New IVR Flow</DialogTitle>
            <DialogDescription className="text-gray-500">
              Create a new interactive voice response flow for your campaigns.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="name" className="text-gray-700">Flow Name</Label>
              <Input
                id="name"
                placeholder="e.g., Main Menu"
                value={newFlowName}
                onChange={(e) => setNewFlowName(e.target.value)}
                className="bg-gray-50 border-gray-200 focus:bg-white"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="description" className="text-gray-700">Description (optional)</Label>
              <Textarea
                id="description"
                placeholder="Describe what this flow does"
                value={newFlowDescription}
                onChange={(e) => setNewFlowDescription(e.target.value)}
                className="bg-gray-50 border-gray-200 focus:bg-white resize-none"
              />
            </div>
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setCreateDialogOpen(false)}
              disabled={creating}
              className="border-gray-200"
            >
              Cancel
            </Button>
            <Button
              onClick={handleCreateFlow}
              disabled={creating || !newFlowName.trim()}
              className="bg-gradient-to-r from-violet-600 to-purple-600 hover:from-violet-700 hover:to-purple-700"
            >
              {creating ? 'Creating...' : 'Create Flow'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
