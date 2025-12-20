import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ArrowLeft,
  Play,
  Pause,
  XCircle,
  Phone,
  Users,
  CheckCircle2,
  AlertCircle,
  Wifi,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
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
import { useToast } from '@/hooks/use-toast';
import { campaignsApi } from '@/services/api';
import { CampaignStatusBadge } from './CampaignStatusBadge';
import { SendReportDialog } from './SendReportDialog';
import { useCampaignProgress } from '@/contexts/WebSocketContext';
import type { ContactStatus } from '@/types';

interface CampaignDetailProps {
  campaignId: string;
  onBack: () => void;
  onEdit: () => void;
}

const contactStatusLabels: Record<ContactStatus, string> = {
  pending: 'Pending',
  in_progress: 'In Progress',
  completed: 'Completed',
  failed: 'Failed',
  dnc: 'DNC',
  skipped: 'Skipped',
};

export function CampaignDetail({ campaignId, onBack, onEdit }: CampaignDetailProps) {
  const [contactsPage, setContactsPage] = useState(1);
  const [contactStatusFilter, setContactStatusFilter] = useState<ContactStatus | 'all'>('all');

  const { toast } = useToast();
  const queryClient = useQueryClient();

  // WebSocket real-time progress updates
  const wsProgress = useCampaignProgress(campaignId);

  // Fetch campaign details - reduce polling frequency since we have WebSocket
  const { data: campaign, isLoading: campaignLoading } = useQuery({
    queryKey: ['campaign', campaignId],
    queryFn: () => campaignsApi.get(campaignId),
    refetchInterval: (query) => (query.state.data?.status === 'running' ? 15000 : false), // Reduced from 5s to 15s
  });

  // Fetch campaign stats - reduce polling frequency since we have WebSocket
  const { data: stats } = useQuery({
    queryKey: ['campaign-stats', campaignId],
    queryFn: () => campaignsApi.getStats(campaignId),
    refetchInterval: () => (campaign?.status === 'running' ? 15000 : false), // Reduced from 5s to 15s
  });

  // Invalidate queries when WebSocket updates indicate status change
  useEffect(() => {
    if (wsProgress && wsProgress.status !== campaign?.status) {
      queryClient.invalidateQueries({ queryKey: ['campaign', campaignId] });
      queryClient.invalidateQueries({ queryKey: ['campaigns'] });
    }
  }, [wsProgress?.status, campaign?.status, campaignId, queryClient]);

  // Fetch campaign contacts
  const { data: contactsData, isLoading: contactsLoading } = useQuery({
    queryKey: ['campaign-contacts', campaignId, contactsPage, contactStatusFilter],
    queryFn: () =>
      campaignsApi.listContacts(campaignId, {
        page: contactsPage,
        page_size: 20,
        status: contactStatusFilter === 'all' ? undefined : contactStatusFilter,
      }),
    enabled: !!campaign,
  });

  // Mutations
  const startMutation = useMutation({
    mutationFn: () => campaignsApi.start(campaignId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['campaign', campaignId] });
      queryClient.invalidateQueries({ queryKey: ['campaigns'] });
      toast({ title: 'Campaign started' });
    },
    onError: (error: Error) => {
      toast({ title: 'Error', description: error.message, variant: 'destructive' });
    },
  });

  const pauseMutation = useMutation({
    mutationFn: () => campaignsApi.pause(campaignId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['campaign', campaignId] });
      queryClient.invalidateQueries({ queryKey: ['campaigns'] });
      toast({ title: 'Campaign paused' });
    },
    onError: (error: Error) => {
      toast({ title: 'Error', description: error.message, variant: 'destructive' });
    },
  });

  const resumeMutation = useMutation({
    mutationFn: () => campaignsApi.resume(campaignId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['campaign', campaignId] });
      queryClient.invalidateQueries({ queryKey: ['campaigns'] });
      toast({ title: 'Campaign resumed' });
    },
    onError: (error: Error) => {
      toast({ title: 'Error', description: error.message, variant: 'destructive' });
    },
  });

  const cancelMutation = useMutation({
    mutationFn: () => campaignsApi.cancel(campaignId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['campaign', campaignId] });
      queryClient.invalidateQueries({ queryKey: ['campaigns'] });
      toast({ title: 'Campaign cancelled' });
    },
    onError: (error: Error) => {
      toast({ title: 'Error', description: error.message, variant: 'destructive' });
    },
  });

  if (campaignLoading) {
    return <div className="text-center py-8">Loading campaign...</div>;
  }

  if (!campaign) {
    return <div className="text-center py-8">Campaign not found</div>;
  }

  const canStart = campaign.status === 'draft' || campaign.status === 'scheduled';
  const canPause = campaign.status === 'running';
  const canResume = campaign.status === 'paused';
  const canCancel =
    campaign.status === 'draft' ||
    campaign.status === 'scheduled' ||
    campaign.status === 'running' ||
    campaign.status === 'paused';
  const canEdit = campaign.status === 'draft';

  // Use WebSocket data if available, otherwise fall back to API data
  const totalContacts = wsProgress?.total_contacts ?? stats?.total_contacts ?? campaign.total_contacts;
  const contactsCompleted = wsProgress?.contacts_completed ?? campaign.contacts_completed;
  const contactsCalled = wsProgress?.contacts_called ?? stats?.total_calls ?? campaign.contacts_called;
  const contactsAnswered = wsProgress?.contacts_answered ?? (stats ? (stats.answered_human + stats.answered_machine) : 0);
  const answerRate = wsProgress?.answer_rate ?? stats?.answer_rate ?? 0;

  const getProgress = () => {
    if (totalContacts === 0) return 0;
    return Math.round((contactsCompleted / totalContacts) * 100);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={onBack}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold">{campaign.name}</h1>
              <CampaignStatusBadge status={campaign.status} />
            </div>
            {campaign.description && (
              <p className="text-muted-foreground">{campaign.description}</p>
            )}
          </div>
        </div>
        <div className="flex gap-2">
          <SendReportDialog campaignId={campaignId} campaignName={campaign.name} />
          {canEdit && (
            <Button variant="outline" onClick={onEdit}>
              Edit
            </Button>
          )}
          {canStart && (
            <Button onClick={() => startMutation.mutate()} className="bg-green-600 hover:bg-green-700">
              <Play className="mr-2 h-4 w-4" />
              Start
            </Button>
          )}
          {canPause && (
            <Button variant="secondary" onClick={() => pauseMutation.mutate()}>
              <Pause className="mr-2 h-4 w-4" />
              Pause
            </Button>
          )}
          {canResume && (
            <Button onClick={() => resumeMutation.mutate()} className="bg-green-600 hover:bg-green-700">
              <Play className="mr-2 h-4 w-4" />
              Resume
            </Button>
          )}
          {canCancel && (
            <Button variant="destructive" onClick={() => cancelMutation.mutate()}>
              <XCircle className="mr-2 h-4 w-4" />
              Cancel
            </Button>
          )}
        </div>
      </div>

      {/* Progress Card */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-lg">Progress</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="flex items-center gap-2">
                {contactsCompleted} / {totalContacts} contacts completed
                {wsProgress && (
                  <span className="flex items-center gap-1 text-xs text-green-600">
                    <Wifi className="w-3 h-3" />
                    Live
                  </span>
                )}
              </span>
              <span className="font-medium">{getProgress()}%</span>
            </div>
            <Progress value={getProgress()} className="h-3" />
          </div>
        </CardContent>
      </Card>

      {/* Stats Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Contacts</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{totalContacts}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Calls</CardTitle>
            <Phone className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{contactsCalled}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Answer Rate</CardTitle>
            <CheckCircle2 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{answerRate.toFixed(1)}%</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Answered</CardTitle>
            <AlertCircle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{contactsAnswered}</div>
          </CardContent>
        </Card>
      </div>

      {/* Detailed Stats */}
      {stats && (
        <div className="grid gap-4 md:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Contact Status</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Pending</span>
                  <span>{stats.contacts_pending}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">In Progress</span>
                  <span>{stats.contacts_in_progress}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Completed</span>
                  <span className="text-green-600">{stats.contacts_completed}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Failed</span>
                  <span className="text-red-600">{stats.contacts_failed}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">DNC</span>
                  <span>{stats.contacts_dnc}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Skipped</span>
                  <span>{stats.contacts_skipped}</span>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Call Outcomes</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Answered (Human)</span>
                  <span className="text-green-600">{stats.answered_human}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Answered (Machine)</span>
                  <span>{stats.answered_machine}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">No Answer</span>
                  <span>{stats.no_answer}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Busy</span>
                  <span>{stats.busy}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Failed</span>
                  <span className="text-red-600">{stats.failed}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Invalid Number</span>
                  <span>{stats.invalid_number}</span>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Contacts Table */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg">Campaign Contacts</CardTitle>
            <Select
              value={contactStatusFilter}
              onValueChange={(v) => {
                setContactStatusFilter(v as ContactStatus | 'all');
                setContactsPage(1);
              }}
            >
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Filter by status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All statuses</SelectItem>
                <SelectItem value="pending">Pending</SelectItem>
                <SelectItem value="in_progress">In Progress</SelectItem>
                <SelectItem value="completed">Completed</SelectItem>
                <SelectItem value="failed">Failed</SelectItem>
                <SelectItem value="dnc">DNC</SelectItem>
                <SelectItem value="skipped">Skipped</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardHeader>
        <CardContent>
          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Phone Number</TableHead>
                  <TableHead>Name</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Attempts</TableHead>
                  <TableHead>Last Disposition</TableHead>
                  <TableHead>Last Attempt</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {contactsLoading ? (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center py-8">
                      Loading...
                    </TableCell>
                  </TableRow>
                ) : contactsData?.items.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center py-8">
                      <p className="text-muted-foreground">No contacts found</p>
                    </TableCell>
                  </TableRow>
                ) : (
                  contactsData?.items.map((contact) => (
                    <TableRow key={contact.id}>
                      <TableCell className="font-mono">{contact.phone_number}</TableCell>
                      <TableCell>
                        {contact.first_name || contact.last_name
                          ? `${contact.first_name || ''} ${contact.last_name || ''}`.trim()
                          : '-'}
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline">{contactStatusLabels[contact.status]}</Badge>
                      </TableCell>
                      <TableCell>{contact.attempts}</TableCell>
                      <TableCell>
                        {contact.last_disposition
                          ? contact.last_disposition.replace('_', ' ')
                          : '-'}
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {contact.last_attempt_at
                          ? new Date(contact.last_attempt_at).toLocaleString()
                          : '-'}
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>

          {contactsData && contactsData.total > 20 && (
            <div className="flex items-center justify-between mt-4">
              <p className="text-sm text-muted-foreground">
                Showing {(contactsPage - 1) * 20 + 1} to{' '}
                {Math.min(contactsPage * 20, contactsData.total)} of {contactsData.total} contacts
              </p>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setContactsPage((p) => Math.max(1, p - 1))}
                  disabled={contactsPage === 1}
                >
                  Previous
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setContactsPage((p) => p + 1)}
                  disabled={contactsPage * 20 >= contactsData.total}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
