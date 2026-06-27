import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'

interface StatusBadgeProps {
  status: 'pending' | 'running' | 'completed' | 'failed' | 'stopped'
}

export function StatusBadge({ status }: StatusBadgeProps) {
  const variants = {
    pending: { variant: 'secondary' as const, label: 'Pending', className: '' },
    running: { variant: 'brand' as const, label: 'Running', className: 'animate-pulse' },
    completed: { variant: 'success' as const, label: 'Completed', className: '' },
    failed: { variant: 'destructive' as const, label: 'Failed', className: '' },
    stopped: { variant: 'warning' as const, label: 'Stopped', className: '' },
  }
  
  const config = variants[status]
  
  return (
    <Badge variant={config.variant} className={cn(config.className)}>
      {config.label}
    </Badge>
  )
}
