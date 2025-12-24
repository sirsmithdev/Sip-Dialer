import { useState } from 'react';
import { BarChart3, Activity, ShieldCheck, FileText } from 'lucide-react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card } from '@/components/ui/card';
import { CallAnalyticsReport } from '@/components/reports/CallAnalyticsReport';
import { RealTimeMonitoring } from '@/components/reports/RealTimeMonitoring';
import { cn } from '@/lib/utils';

export function ReportsPage() {
  const [activeTab, setActiveTab] = useState('call-analytics');

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <div className="p-3 rounded-xl bg-gradient-to-br from-violet-500 to-purple-600 shadow-lg shadow-violet-500/25">
          <BarChart3 className="h-6 w-6 text-white" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Reports & Analytics</h1>
          <p className="text-gray-500">Monitor your campaign performance and call metrics</p>
        </div>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="bg-gray-100/80 p-1 h-auto">
          <TabsTrigger
            value="call-analytics"
            className={cn(
              'data-[state=active]:bg-white data-[state=active]:shadow-sm',
              'flex items-center gap-2 px-4 py-2.5'
            )}
          >
            <BarChart3 className="h-4 w-4" />
            Call Analytics
          </TabsTrigger>
          <TabsTrigger
            value="real-time"
            className={cn(
              'data-[state=active]:bg-white data-[state=active]:shadow-sm',
              'flex items-center gap-2 px-4 py-2.5'
            )}
          >
            <Activity className="h-4 w-4" />
            Real-Time Monitoring
          </TabsTrigger>
          <TabsTrigger
            value="compliance"
            className={cn(
              'data-[state=active]:bg-white data-[state=active]:shadow-sm',
              'flex items-center gap-2 px-4 py-2.5'
            )}
          >
            <ShieldCheck className="h-4 w-4" />
            Compliance
          </TabsTrigger>
        </TabsList>

        <TabsContent value="call-analytics" className="mt-6">
          <CallAnalyticsReport />
        </TabsContent>

        <TabsContent value="real-time" className="mt-6">
          <RealTimeMonitoring />
        </TabsContent>

        <TabsContent value="compliance" className="mt-6">
          <Card className="border-0 shadow-lg shadow-gray-200/50">
            <div className="flex flex-col items-center justify-center py-16 px-6">
              <div className="p-4 rounded-full bg-gradient-to-br from-violet-100 to-purple-100 mb-4">
                <FileText className="h-10 w-10 text-violet-500" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                Compliance Reports Coming Soon
              </h3>
              <p className="text-gray-500 text-center max-w-md">
                We're working on comprehensive compliance reporting including TCPA regulations,
                DNC list compliance, and call recording audits.
              </p>
            </div>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
