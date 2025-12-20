import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Search, MoreHorizontal, Trash2, Play, Pause, XCircle, Eye, Edit } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { usePermissions } from '@/hooks/use-permissions';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Progress } from '@/components/ui/progress';
import { useToast } from '@/hooks/use-toast';
import { campaignsApi } from '@/services/api';
import { CampaignStatusBadge } from './CampaignStatusBadge';
import type { CampaignListItem, CampaignStatus } from '@/types';

interface CampaignsTableProps {
  onViewCampaign: (campaign: CampaignListItem) => void;
  onEditCampaign: (campaign: CampaignListItem) => void;
}

export function CampaignsTable({ onViewCampaign, onEditCampaign }: CampaignsTableProps) {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<CampaignStatus | 'all'>('all');
  const [deleteId, setDeleteId] = useState<string | null>(null);

  const { toast } = useToast();
  const queryClient = useQueryClient();
  const { hasPermission } = usePermissions();

  // Permission checks
  const canEditCampaigns = hasPermission('campaigns.edit');
  const canDeleteCampaigns = hasPermission('campaigns.delete');
  const canControlCampaigns = hasPermission('campaigns.control');

  const { data, isLoading } = useQuery({
    queryKey: ['campaigns', page, search, statusFilter],
    queryFn: () =>
      campaignsApi.list({
        page,
        page_size: 20,
        search: search || undefined,
        status: statusFilter === 'all' ? undefined : statusFilter,
      }),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => campaignsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['campaigns'] });
      toast({
        title: 'Campaign deleted',
        description: 'The campaign has been deleted.',
      });
    },
    onError: (error: Error) => {
      toast({
        title: 'Error',
        description: error.message || 'Failed to delete campaign.',
        variant: 'destructive',
      });
    },
  });

  const startMutation = useMutation({
    mutationFn: (id: string) => campaignsApi.start(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['campaigns'] });
      toast({ title: 'Campaign started', description: 'The campaign is now running.' });
    },
    onError: (error: Error) => {
      toast({ title: 'Error', description: error.message, variant: 'destructive' });
    },
  });

  const pauseMutation = useMutation({
    mutationFn: (id: string) => campaignsApi.pause(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['campaigns'] });
      toast({ title: 'Campaign paused', description: 'The campaign has been paused.' });
    },
    onError: (error: Error) => {
      toast({ title: 'Error', description: error.message, variant: 'destructive' });
    },
  });

  const resumeMutation = useMutation({
    mutationFn: (id: string) => campaignsApi.resume(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['campaigns'] });
      toast({ title: 'Campaign resumed', description: 'The campaign is now running.' });
    },
    onError: (error: Error) => {
      toast({ title: 'Error', description: error.message, variant: 'destructive' });
    },
  });

  const cancelMutation = useMutation({
    mutationFn: (id: string) => campaignsApi.cancel(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['campaigns'] });
      toast({ title: 'Campaign cancelled', description: 'The campaign has been cancelled.' });
    },
    onError: (error: Error) => {
      toast({ title: 'Error', description: error.message, variant: 'destructive' });
    },
  });

  const handleDelete = () => {
    if (deleteId) {
      deleteMutation.mutate(deleteId);
      setDeleteId(null);
    }
  };

  const getProgress = (campaign: CampaignListItem) => {
    if (campaign.total_contacts === 0) return 0;
    return Math.round((campaign.contacts_completed / campaign.total_contacts) * 100);
  };

  const canStart = (status: CampaignStatus) => status === 'draft' || status === 'scheduled';
  const canPause = (status: CampaignStatus) => status === 'running';
  const canResume = (status: CampaignStatus) => status === 'paused';
  const canCancel = (status: CampaignStatus) =>
    status === 'draft' || status === 'scheduled' || status === 'running' || status === 'paused';
  const canDelete = (status: CampaignStatus) => status === 'draft' || status === 'cancelled';
  const canEdit = (status: CampaignStatus) => status === 'draft';

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search campaigns..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            className="pl-9"
          />
        </div>
        <Select
          value={statusFilter}
          onValueChange={(value) => {
            setStatusFilter(value as CampaignStatus | 'all');
            setPage(1);
          }}
        >
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="Filter by status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All statuses</SelectItem>
            <SelectItem value="draft">Draft</SelectItem>
            <SelectItem value="scheduled">Scheduled</SelectItem>
            <SelectItem value="running">Running</SelectItem>
            <SelectItem value="paused">Paused</SelectItem>
            <SelectItem value="completed">Completed</SelectItem>
            <SelectItem value="cancelled">Cancelled</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Progress</TableHead>
              <TableHead>Contacts</TableHead>
              <TableHead>Answered</TableHead>
              <TableHead>Created</TableHead>
              <TableHead className="w-[50px]"></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center py-8">
                  Loading...
                </TableCell>
              </TableRow>
            ) : data?.items.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center py-8">
                  <p className="text-muted-foreground">No campaigns found</p>
                </TableCell>
              </TableRow>
            ) : (
              data?.items.map((campaign) => (
                <TableRow key={campaign.id}>
                  <TableCell>
                    <div>
                      <button
                        onClick={() => onViewCampaign(campaign)}
                        className="font-medium hover:underline text-left"
                      >
                        {campaign.name}
                      </button>
                      {campaign.description && (
                        <p className="text-xs text-muted-foreground truncate max-w-[200px]">
                          {campaign.description}
                        </p>
                      )}
                    </div>
                  </TableCell>
                  <TableCell>
                    <CampaignStatusBadge status={campaign.status} />
                  </TableCell>
                  <TableCell>
                    <div className="w-[100px]">
                      <Progress value={getProgress(campaign)} className="h-2" />
                      <p className="text-xs text-muted-foreground mt-1">
                        {getProgress(campaign)}%
                      </p>
                    </div>
                  </TableCell>
                  <TableCell>
                    {campaign.contacts_called} / {campaign.total_contacts}
                  </TableCell>
                  <TableCell>{campaign.contacts_answered}</TableCell>
                  <TableCell className="text-muted-foreground">
                    {new Date(campaign.created_at).toLocaleDateString()}
                  </TableCell>
                  <TableCell>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="icon">
                          <MoreHorizontal className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem onClick={() => onViewCampaign(campaign)}>
                          <Eye className="mr-2 h-4 w-4" />
                          View
                        </DropdownMenuItem>
                        {canEditCampaigns && canEdit(campaign.status) && (
                          <DropdownMenuItem onClick={() => onEditCampaign(campaign)}>
                            <Edit className="mr-2 h-4 w-4" />
                            Edit
                          </DropdownMenuItem>
                        )}
                        {canControlCampaigns && (
                          <>
                            <DropdownMenuSeparator />
                            {canStart(campaign.status) && (
                              <DropdownMenuItem
                                onClick={() => startMutation.mutate(campaign.id)}
                                className="text-green-600"
                              >
                                <Play className="mr-2 h-4 w-4" />
                                Start
                              </DropdownMenuItem>
                            )}
                            {canPause(campaign.status) && (
                              <DropdownMenuItem onClick={() => pauseMutation.mutate(campaign.id)}>
                                <Pause className="mr-2 h-4 w-4" />
                                Pause
                              </DropdownMenuItem>
                            )}
                            {canResume(campaign.status) && (
                              <DropdownMenuItem
                                onClick={() => resumeMutation.mutate(campaign.id)}
                                className="text-green-600"
                              >
                                <Play className="mr-2 h-4 w-4" />
                                Resume
                              </DropdownMenuItem>
                            )}
                            {canCancel(campaign.status) && (
                              <DropdownMenuItem
                                onClick={() => cancelMutation.mutate(campaign.id)}
                                className="text-orange-600"
                              >
                                <XCircle className="mr-2 h-4 w-4" />
                                Cancel
                              </DropdownMenuItem>
                            )}
                          </>
                        )}
                        {canDeleteCampaigns && canDelete(campaign.status) && (
                          <>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem
                              className="text-destructive"
                              onClick={() => setDeleteId(campaign.id)}
                            >
                              <Trash2 className="mr-2 h-4 w-4" />
                              Delete
                            </DropdownMenuItem>
                          </>
                        )}
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {data && data.total > 20 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            Showing {(page - 1) * 20 + 1} to {Math.min(page * 20, data.total)} of {data.total}{' '}
            campaigns
          </p>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
            >
              Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => p + 1)}
              disabled={page * 20 >= data.total}
            >
              Next
            </Button>
          </div>
        </div>
      )}

      <AlertDialog open={!!deleteId} onOpenChange={() => setDeleteId(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete campaign?</AlertDialogTitle>
            <AlertDialogDescription>
              This action cannot be undone. This will permanently delete the campaign and all
              associated data.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleDelete} className="bg-destructive text-destructive-foreground">
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
