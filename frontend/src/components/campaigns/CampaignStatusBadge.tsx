import { Badge } from '@/components/ui/badge';
import type { CampaignStatus } from '@/types';

interface CampaignStatusBadgeProps {
  status: CampaignStatus;
}

const statusConfig: Record<CampaignStatus, { label: string; variant: 'default' | 'secondary' | 'destructive' | 'outline' }> = {
  draft: { label: 'Draft', variant: 'outline' },
  scheduled: { label: 'Scheduled', variant: 'secondary' },
  running: { label: 'Running', variant: 'default' },
  paused: { label: 'Paused', variant: 'secondary' },
  completed: { label: 'Completed', variant: 'outline' },
  cancelled: { label: 'Cancelled', variant: 'destructive' },
};

export function CampaignStatusBadge({ status }: CampaignStatusBadgeProps) {
  const config = statusConfig[status];

  return (
    <Badge variant={config.variant} className={status === 'running' ? 'bg-green-600' : undefined}>
      {config.label}
    </Badge>
  );
}
