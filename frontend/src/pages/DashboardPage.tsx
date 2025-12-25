import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/hooks/use-auth';
import { useWebSocketContext, useSIPStatus } from '@/contexts/WebSocketContext';
import { useNavigate } from 'react-router-dom';
import { campaignsApi, sipSettingsApi } from '@/services/api';
import {
  Phone,
  PhoneOutgoing,
  TrendingUp,
  CheckCircle2,
  Plus,
  Upload,
  Settings,
  Music,
  ArrowRight,
  Activity,
  Users,
  Clock,
  Wifi,
  WifiOff,
  AlertCircle,
  Loader2,
} from 'lucide-react';

function SIPStatusIndicator() {
  const sipStatus = useSIPStatus();
  const { isConnected: wsConnected } = useWebSocketContext();

  // Check if WebSocket status is stale (over 60 seconds old)
  const isStatusStale = sipStatus?.last_updated
    ? new Date().getTime() - new Date(sipStatus.last_updated).getTime() > 60000
    : true;

  // Determine if we need to poll for status
  const needsPolling = !sipStatus || sipStatus.status === 'unknown' || isStatusStale;

  // Fallback: Query SIP settings from database when WebSocket status is unavailable
  const { data: sipSettings, isLoading: settingsLoading } = useQuery({
    queryKey: ['sip-settings-status'],
    queryFn: sipSettingsApi.get,
    enabled: needsPolling,
    staleTime: 30000, // Cache for 30 seconds
    retry: 1,
  });

  // Also try to get real-time dialer status as fallback (more frequent when WS unavailable)
  const { data: dialerStatus, isLoading: dialerLoading } = useQuery({
    queryKey: ['dialer-status'],
    queryFn: sipSettingsApi.getDialerStatus,
    enabled: needsPolling,
    staleTime: 5000, // Cache for 5 seconds only
    refetchInterval: needsPolling ? 10000 : 30000, // Poll every 10s when needed, 30s otherwise
    retry: 2,
  });

  // Determine the effective status to display
  const effectiveStatus = (() => {
    // Priority 1: WebSocket real-time status
    if (sipStatus && sipStatus.status !== 'unknown') {
      return {
        status: sipStatus.status,
        extension: sipStatus.extension,
        active_calls: sipStatus.active_calls || 0,
      };
    }

    // Priority 2: Dialer status from API (Redis)
    if (dialerStatus?.sip && dialerStatus.sip.status !== 'unknown') {
      return {
        status: dialerStatus.sip.status,
        extension: dialerStatus.sip.extension,
        active_calls: dialerStatus.sip.active_calls || 0,
      };
    }

    // Priority 3: SIP settings from database
    if (sipSettings?.connection_status) {
      return {
        status: sipSettings.connection_status,
        extension: sipSettings.extension,
        active_calls: 0,
      };
    }

    return null;
  })();

  if (!wsConnected && !effectiveStatus) {
    return (
      <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-muted text-muted-foreground text-sm">
        <WifiOff className="w-4 h-4" />
        <span>Connecting...</span>
      </div>
    );
  }

  if (settingsLoading || dialerLoading) {
    return (
      <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-muted text-muted-foreground text-sm">
        <Loader2 className="w-4 h-4 animate-spin" />
        <span>Loading...</span>
      </div>
    );
  }

  if (!effectiveStatus) {
    return (
      <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-muted text-muted-foreground text-sm">
        <AlertCircle className="w-4 h-4" />
        <span>SIP Not Configured</span>
      </div>
    );
  }

  const statusColors: Record<string, { bg: string; text: string; dot: string }> = {
    registered: { bg: 'bg-green-500/10', text: 'text-green-600', dot: 'bg-green-500' },
    connecting: { bg: 'bg-yellow-500/10', text: 'text-yellow-600', dot: 'bg-yellow-500' },
    disconnected: { bg: 'bg-gray-500/10', text: 'text-gray-600', dot: 'bg-gray-500' },
    failed: { bg: 'bg-red-500/10', text: 'text-red-600', dot: 'bg-red-500' },
  };

  const colors = statusColors[effectiveStatus.status] || statusColors.disconnected;

  return (
    <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full ${colors.bg} ${colors.text} text-sm`}>
      <span className={`w-2 h-2 rounded-full ${colors.dot} ${effectiveStatus.status === 'registered' ? 'animate-pulse' : ''}`} />
      <Wifi className="w-4 h-4" />
      <span className="capitalize">{effectiveStatus.status}</span>
      {effectiveStatus.extension && <span className="opacity-75">({effectiveStatus.extension})</span>}
      {effectiveStatus.active_calls > 0 && (
        <span className="ml-1 px-1.5 py-0.5 bg-primary/20 rounded text-xs">
          {effectiveStatus.active_calls} call{effectiveStatus.active_calls > 1 ? 's' : ''}
        </span>
      )}
    </div>
  );
}

export function DashboardPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const { dashboardStats } = useWebSocketContext();

  // Fetch campaigns for stats
  const { data: campaignsData } = useQuery({
    queryKey: ['campaigns-stats'],
    queryFn: () => campaignsApi.list({ page: 1, page_size: 100 }),
    refetchInterval: 30000, // Fallback polling every 30s
  });

  // Calculate stats from data
  const campaigns = campaignsData?.items || [];
  const activeCampaigns = campaigns.filter((c) => c.status === 'running').length;
  const completedCampaigns = campaigns.filter((c) => c.status === 'completed').length;

  // Use WebSocket stats if available, otherwise use calculated values
  const stats = [
    {
      title: 'Active Campaigns',
      value: String(dashboardStats?.active_campaigns ?? activeCampaigns),
      description: 'Currently running',
      icon: Phone,
      color: 'text-green-500',
      bgColor: 'bg-green-500/10',
    },
    {
      title: 'Calls Today',
      value: String(dashboardStats?.calls_today ?? 0),
      description: 'Total outbound calls',
      icon: PhoneOutgoing,
      color: 'text-blue-500',
      bgColor: 'bg-blue-500/10',
    },
    {
      title: 'Answer Rate',
      value: `${(dashboardStats?.answer_rate ?? 0).toFixed(1)}%`,
      description: "Today's performance",
      icon: TrendingUp,
      color: 'text-purple-500',
      bgColor: 'bg-purple-500/10',
    },
    {
      title: 'Calls Answered',
      value: String(dashboardStats?.calls_answered ?? 0),
      description: "Today's answered",
      icon: CheckCircle2,
      color: 'text-orange-500',
      bgColor: 'bg-orange-500/10',
    },
  ];

  const quickActions = [
    {
      title: 'Create Campaign',
      description: 'Set up a new outbound calling campaign',
      icon: Plus,
      onClick: () => navigate('/campaigns'),
      color: 'text-purple-500',
      bgColor: 'bg-purple-500/10',
    },
    {
      title: 'Upload Contacts',
      description: 'Import your contact list from CSV',
      icon: Upload,
      onClick: () => navigate('/contacts'),
      color: 'text-blue-500',
      bgColor: 'bg-blue-500/10',
    },
    {
      title: 'Configure IVR',
      description: 'Design your interactive voice response flow',
      icon: Settings,
      onClick: () => navigate('/ivr'),
      color: 'text-green-500',
      bgColor: 'bg-green-500/10',
    },
    {
      title: 'Upload Audio',
      description: 'Add voice prompts and recordings',
      icon: Music,
      onClick: () => navigate('/audio'),
      color: 'text-orange-500',
      bgColor: 'bg-orange-500/10',
    },
  ];

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-col gap-2">
          <div className="flex items-center gap-2">
            <h1 className="text-3xl font-bold">Dashboard</h1>
          </div>
          <p className="text-muted-foreground text-lg">
            Welcome back, <span className="text-foreground font-medium">{user?.first_name || user?.email}</span>
          </p>
        </div>
        <SIPStatusIndicator />
      </div>

      {/* Stats Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat, index) => (
          <Card key={stat.title} className="card-hover overflow-hidden" style={{ animationDelay: `${index * 0.1}s` }}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                {stat.title}
              </CardTitle>
              <div className={`w-10 h-10 rounded-lg ${stat.bgColor} flex items-center justify-center`}>
                <stat.icon className={`w-5 h-5 ${stat.color}`} />
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">{stat.value}</div>
              <p className="text-xs text-muted-foreground mt-1">
                {stat.description}
              </p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Main Content Grid */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Recent Activity */}
        <Card className="lg:col-span-2 card-hover">
          <CardHeader className="flex flex-row items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-purple-500/10 flex items-center justify-center">
                <Activity className="w-5 h-5 text-purple-500" />
              </div>
              <div>
                <CardTitle>Recent Activity</CardTitle>
                <p className="text-sm text-muted-foreground">Your latest campaign activity</p>
              </div>
            </div>
            <Button variant="ghost" size="sm" className="text-primary" onClick={() => navigate('/campaigns')}>
              View All
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          </CardHeader>
          <CardContent>
            {campaigns.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <div className="w-16 h-16 rounded-full bg-muted/50 flex items-center justify-center mb-4">
                  <Phone className="w-8 h-8 text-muted-foreground" />
                </div>
                <h3 className="font-semibold mb-2">No campaigns yet</h3>
                <p className="text-sm text-muted-foreground max-w-sm">
                  Create your first campaign to start making outbound calls and see activity here.
                </p>
                <Button className="mt-4 gradient-primary" onClick={() => navigate('/campaigns')}>
                  <Plus className="mr-2 h-4 w-4" />
                  Create Campaign
                </Button>
              </div>
            ) : (
              <div className="space-y-3">
                {campaigns.slice(0, 5).map((campaign) => (
                  <div
                    key={campaign.id}
                    className="flex items-center justify-between p-3 rounded-lg bg-muted/50 hover:bg-muted cursor-pointer transition-colors"
                    onClick={() => navigate('/campaigns')}
                  >
                    <div className="flex items-center gap-3">
                      <div className={`w-2 h-2 rounded-full ${
                        campaign.status === 'running' ? 'bg-green-500 animate-pulse' :
                        campaign.status === 'completed' ? 'bg-blue-500' :
                        campaign.status === 'paused' ? 'bg-yellow-500' :
                        'bg-gray-500'
                      }`} />
                      <div>
                        <p className="font-medium text-sm">{campaign.name}</p>
                        <p className="text-xs text-muted-foreground capitalize">{campaign.status}</p>
                      </div>
                    </div>
                    <ArrowRight className="w-4 h-4 text-muted-foreground" />
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Quick Actions */}
        <Card className="card-hover">
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-blue-500/10 flex items-center justify-center">
                <Settings className="w-5 h-5 text-blue-500" />
              </div>
              <div>
                <CardTitle>Quick Actions</CardTitle>
                <p className="text-sm text-muted-foreground">Common tasks</p>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            {quickActions.map((action) => (
              <button
                key={action.title}
                onClick={action.onClick}
                className="w-full flex items-center gap-3 p-3 rounded-lg hover:bg-muted/50 transition-colors text-left group"
              >
                <div className={`w-9 h-9 rounded-lg ${action.bgColor} flex items-center justify-center flex-shrink-0`}>
                  <action.icon className={`w-4 h-4 ${action.color}`} />
                </div>
                <div className="flex-1 min-w-0">
                  <h4 className="font-medium text-sm group-hover:text-primary transition-colors">
                    {action.title}
                  </h4>
                  <p className="text-xs text-muted-foreground truncate">
                    {action.description}
                  </p>
                </div>
                <ArrowRight className="w-4 h-4 text-muted-foreground group-hover:text-primary transition-colors opacity-0 group-hover:opacity-100" />
              </button>
            ))}
          </CardContent>
        </Card>
      </div>

      {/* Bottom Stats Row */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card className="card-hover">
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-xl bg-purple-500/10 flex items-center justify-center">
                <Users className="w-6 h-6 text-purple-500" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Total Contacts</p>
                <p className="text-2xl font-bold">{dashboardStats?.total_contacts ?? 0}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="card-hover">
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-xl bg-green-500/10 flex items-center justify-center">
                <CheckCircle2 className="w-6 h-6 text-green-500" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Completed Campaigns</p>
                <p className="text-2xl font-bold">{dashboardStats?.completed_campaigns ?? completedCampaigns}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="card-hover">
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-xl bg-blue-500/10 flex items-center justify-center">
                <Clock className="w-6 h-6 text-blue-500" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Avg. Call Duration</p>
                <p className="text-2xl font-bold">{Math.round(dashboardStats?.avg_call_duration ?? 0)}s</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
