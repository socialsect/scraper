import Link from 'next/link'
import { Job } from '@/lib/api'
import { StatusBadge } from './status-badge'
import { timeAgo } from '@/lib/utils'
import { Badge } from './ui/badge'

interface JobCardProps {
  job: Job
}

export function JobCard({ job }: JobCardProps) {
  return (
    <Link
      href={`/jobs/${job.id}`}
      className="block rounded-lg border border-zinc-800 bg-zinc-900 p-4 transition-colors hover:border-zinc-700 hover:bg-zinc-800/50"
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-2">
            <h3 className="font-medium text-zinc-50 truncate">{job.query}</h3>
            <StatusBadge status={job.status} />
          </div>
          
          <div className="flex items-center gap-3 text-sm text-zinc-400">
            <span className="flex items-center gap-1.5">
              <Badge variant="outline" className="text-xs">
                {job.engine}
              </Badge>
              <Badge variant="outline" className="text-xs">
                {job.backend}
              </Badge>
            </span>
            
            {job.stats.total_emails > 0 && (
              <span>
                <span className="text-brand font-medium">{job.stats.total_emails}</span> emails
              </span>
            )}
            
            <span className="text-zinc-500">{timeAgo(job.created_at)}</span>
          </div>
        </div>
      </div>
    </Link>
  )
}
