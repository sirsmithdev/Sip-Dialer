import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Phone, Users, TrendingUp, Activity, Gauge, PlayCircle } from 'lucide-react';
import { reportsApi } from '@/services/api';

export function RealTimeMonitoring() {
  const { data: metrics, isLoading } = useQuery({
    queryKey: ['real-time-metrics'],
    queryFn: reportsApi.getRealTimeMetrics,
    refetchInterval: 3000, // Poll every 3 seconds
  });

  if (isLoading || !metrics) {
    return <div className="text-center py-12">Loading real-time metrics...</div>;
  }

  const stats = [
    {
      title: 'Active Calls',
      value: metrics.active_calls,
      icon: Phone,
      description: `${metrics.calls_per_minute.toFixed(1)} calls/min`,
      color: 'text-blue-600',
      bgColor: 'bg-blue-100',
    },
    {
      title: 'Queued Calls',
      value: metrics.queued_calls,
      icon: Users,
      description: 'Waiting to dial',
      color: 'text-purple-600',
      bgColor: 'bg-purple-100',
    },
    {
      title: 'Answer Rate',
      value: `${metrics.current_answer_rate.toFixed(1)}%`,
      icon: TrendingUp,
      description: 'Last hour',
      color: 'text-green-600',
      bgColor: 'bg-green-100',
    },
    {
      title: 'Line Utilization',
      value: `${metrics.line_utilization_percent.toFixed(0)}%`,
      icon: Gauge,
      description: 'Current capacity',
      color: 'text-orange-600',
      bgColor: 'bg-orange-100',
    },
    {
      title: 'Active Campaigns',
      value: metrics.active_campaigns_count,
      icon: PlayCircle,
      description: 'Running now',
      color: 'text-indigo-600',
      bgColor: 'bg-indigo-100',
    },
    {
      title: 'Calls/Minute',
      value: metrics.calls_per_minute.toFixed(1),
      icon: Activity,
      description: 'Current rate',
      color: 'text-pink-600',
      bgColor: 'bg-pink-100',
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          Auto-refreshing every 3 seconds
        </p>
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
          Live
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {stats.map((stat) => {
          const Icon = stat.icon;
          return (
            <Card key={stat.title}>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  {stat.title}
                </CardTitle>
                <div className={`p-2 rounded-full ${stat.bgColor}`}>
                  <Icon className={`h-4 w-4 ${stat.color}`} />
                </div>
              </CardHeader>
              <CardContent>
                <div className={`text-2xl font-bold ${stat.color}`}>
                  {stat.value}
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  {stat.description}
                </p>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Capacity Bar */}
      <Card>
        <CardHeader>
          <CardTitle>System Capacity</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span>Line Utilization</span>
              <span className="font-medium">
                {metrics.line_utilization_percent.toFixed(0)}%
              </span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-4 overflow-hidden">
              <div
                className={`h-full transition-all duration-500 ${
                  metrics.line_utilization_percent > 80
                    ? 'bg-red-500'
                    : metrics.line_utilization_percent > 60
                    ? 'bg-yellow-500'
                    : 'bg-green-500'
                }`}
                style={{ width: `${Math.min(metrics.line_utilization_percent, 100)}%` }}
              />
            </div>
            <p className="text-xs text-muted-foreground">
              {metrics.line_utilization_percent > 80
                ? 'High utilization - consider scaling up'
                : metrics.line_utilization_percent > 60
                ? 'Moderate utilization'
                : 'Capacity available'}
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
