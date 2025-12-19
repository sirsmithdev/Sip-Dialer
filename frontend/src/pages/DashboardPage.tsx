import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/hooks/use-auth';
import { useNavigate } from 'react-router-dom';
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
} from 'lucide-react';

export function DashboardPage() {
  const { user } = useAuth();
  const navigate = useNavigate();

  const stats = [
    {
      title: 'Active Campaigns',
      value: '0',
      description: 'Currently running',
      icon: Phone,
      color: 'text-green-500',
      bgColor: 'bg-green-500/10',
    },
    {
      title: 'Calls Today',
      value: '0',
      description: 'Total outbound calls',
      icon: PhoneOutgoing,
      color: 'text-blue-500',
      bgColor: 'bg-blue-500/10',
    },
    {
      title: 'Answer Rate',
      value: '0%',
      description: "Today's performance",
      icon: TrendingUp,
      color: 'text-purple-500',
      bgColor: 'bg-purple-500/10',
    },
    {
      title: 'Surveys Completed',
      value: '0',
      description: "Today's surveys",
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
      onClick: () => navigate('/settings'),
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
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-2">
          <h1 className="text-3xl font-bold">Dashboard</h1>
          <span className="status-dot status-active" />
        </div>
        <p className="text-muted-foreground text-lg">
          Welcome back, <span className="text-foreground font-medium">{user?.first_name || user?.email}</span>
        </p>
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
            <Button variant="ghost" size="sm" className="text-primary">
              View All
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          </CardHeader>
          <CardContent>
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
                <p className="text-2xl font-bold">0</p>
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
                <p className="text-2xl font-bold">0</p>
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
                <p className="text-2xl font-bold">0s</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
