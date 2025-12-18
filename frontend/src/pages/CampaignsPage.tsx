import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { useToast } from '@/hooks/use-toast';
import { campaignsApi } from '@/services/api';
import { CampaignsTable, CampaignForm, CampaignDetail } from '@/components/campaigns';
import type { CampaignListItem, CampaignCreate, CampaignUpdate } from '@/types';

type ViewMode = 'list' | 'detail' | 'create' | 'edit';

export function CampaignsPage() {
  const [viewMode, setViewMode] = useState<ViewMode>('list');
  const [selectedCampaignId, setSelectedCampaignId] = useState<string | null>(null);
  const [editingCampaign, setEditingCampaign] = useState<CampaignListItem | null>(null);

  const { toast } = useToast();
  const queryClient = useQueryClient();

  // Create campaign mutation
  const createMutation = useMutation({
    mutationFn: (data: CampaignCreate) => campaignsApi.create(data),
    onSuccess: (campaign) => {
      queryClient.invalidateQueries({ queryKey: ['campaigns'] });
      setViewMode('detail');
      setSelectedCampaignId(campaign.id);
      toast({
        title: 'Campaign created',
        description: 'Your new campaign has been created successfully.',
      });
    },
    onError: (error: Error) => {
      toast({
        title: 'Error',
        description: error.message || 'Failed to create campaign.',
        variant: 'destructive',
      });
    },
  });

  // Update campaign mutation
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: CampaignUpdate }) =>
      campaignsApi.update(id, data),
    onSuccess: (campaign) => {
      queryClient.invalidateQueries({ queryKey: ['campaigns'] });
      queryClient.invalidateQueries({ queryKey: ['campaign', campaign.id] });
      setViewMode('detail');
      setSelectedCampaignId(campaign.id);
      setEditingCampaign(null);
      toast({
        title: 'Campaign updated',
        description: 'Your campaign has been updated successfully.',
      });
    },
    onError: (error: Error) => {
      toast({
        title: 'Error',
        description: error.message || 'Failed to update campaign.',
        variant: 'destructive',
      });
    },
  });

  const handleViewCampaign = (campaign: CampaignListItem) => {
    setSelectedCampaignId(campaign.id);
    setViewMode('detail');
  };

  const handleEditCampaign = (campaign: CampaignListItem) => {
    setEditingCampaign(campaign);
    setSelectedCampaignId(campaign.id);
    setViewMode('edit');
  };

  const handleBackToList = () => {
    setViewMode('list');
    setSelectedCampaignId(null);
    setEditingCampaign(null);
  };

  const handleCreateSubmit = (data: CampaignCreate | CampaignUpdate) => {
    createMutation.mutate(data as CampaignCreate);
  };

  const handleUpdateSubmit = (data: CampaignCreate | CampaignUpdate) => {
    if (selectedCampaignId) {
      updateMutation.mutate({ id: selectedCampaignId, data: data as CampaignUpdate });
    }
  };

  // Render create dialog
  if (viewMode === 'create') {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold">Create Campaign</h1>
            <p className="text-muted-foreground">Set up a new outbound calling campaign</p>
          </div>
        </div>
        <CampaignForm
          onSubmit={handleCreateSubmit}
          onCancel={handleBackToList}
          isSubmitting={createMutation.isPending}
        />
      </div>
    );
  }

  // Render edit view
  if (viewMode === 'edit' && selectedCampaignId) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold">Edit Campaign</h1>
            <p className="text-muted-foreground">Update campaign settings</p>
          </div>
        </div>
        <CampaignForm
          campaign={editingCampaign as any}
          onSubmit={handleUpdateSubmit}
          onCancel={() => {
            setViewMode('detail');
            setEditingCampaign(null);
          }}
          isSubmitting={updateMutation.isPending}
        />
      </div>
    );
  }

  // Render detail view
  if (viewMode === 'detail' && selectedCampaignId) {
    return (
      <CampaignDetail
        campaignId={selectedCampaignId}
        onBack={handleBackToList}
        onEdit={() => setViewMode('edit')}
      />
    );
  }

  // Render list view
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Campaigns</h1>
          <p className="text-muted-foreground">Manage your auto-dialer campaigns</p>
        </div>
        <Button onClick={() => setViewMode('create')}>
          <Plus className="mr-2 h-4 w-4" />
          New Campaign
        </Button>
      </div>

      <CampaignsTable onViewCampaign={handleViewCampaign} onEditCampaign={handleEditCampaign} />
    </div>
  );
}
