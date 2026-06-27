'use client'

import { useEffect, useState, useRef } from 'react'
import { useRouter, useParams } from 'next/navigation'
import useSWR from 'swr'
import { getJobStatus, stopJob, streamJob, downloadCSV, Job as JobType } from '@/lib/api'
import { StatusBadge } from '@/components/status-badge'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { formatDate, formatDuration, downloadBlob, cn } from '@/lib/utils'
import { Eye, Download, StopCircle } from 'lucide-react'
import Link from 'next/link'

export default function JobPage() {
  const params = useParams()
  const router = useRouter()
  const jobId = params.id as string
  
  const { data: initialJob, mutate } = useSWR(
    jobId ? `/jobs/${jobId}/status` : null,
    () => getJobStatus(jobId),
    { refreshInterval: 3000 }
  )
  
  const [job, setJob] = useState<JobType | null>(null)
  const [isLive, setIsLive] = useState(false)
  const [logs, setLogs] = useState<string[]>([])
  const logsEndRef = useRef<HTMLDivElement>(null)
  
  useEffect(() => {
    if (initialJob) {
      setJob(initialJob)
    }
  }, [initialJob])
  
  useEffect(() => {
    if (!job || job.status !== 'running') {
      setIsLive(false)
      return
    }
    
    setIsLive(true)
    
    const cleanup = streamJob(
      jobId,
      (data) => {
        setJob(prev => {
          if (!prev) return prev
          return {
            ...prev,
            status: data.status || prev.status,
            stats: {
              ...prev.stats,
              ...data.stats,
              elapsed_seconds: data.elapsed_seconds ?? prev.stats.elapsed_seconds,
              pages_crawled: data.pages_crawled ?? prev.stats.pages_crawled,
              new_emails: data.new_emails ?? prev.stats.new_emails,
              total_emails: data.total_emails ?? prev.stats.total_emails,
              last_email: data.last_email ?? prev.stats.last_email,
              queue_size: data.queue_size ?? prev.stats.queue_size,
              errors: data.errors ?? prev.stats.errors,
              rate_per_min: data.rate_per_min ?? prev.stats.rate_per_min,
            },
          }
        })
        
        if (data.last_email) {
          setLogs(prev => [...prev.slice(-99), `Found: ${data.last_email}`])
        }
      },
      () => {
        setIsLive(false)
        mutate()
      },
      (error) => {
        console.error('Stream error:', error)
        setIsLive(false)
      }
    )
    
    return cleanup
  }, [job?.status, jobId, mutate])
  
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs])
  
  useEffect(() => {
    if (job?.status === 'completed' && job.stats?.total_emails > 0) {
      const timer = setTimeout(() => {
        router.push(`/jobs/${jobId}/results`)
      }, 2000)
      return () => clearTimeout(timer)
    }
  }, [job?.status, job?.stats?.total_emails, jobId, router])
  
  const handleStop = async () => {
    if (!job) return
    
    try {
      await stopJob(jobId)
      mutate()
    } catch (error) {
      console.error('Failed to stop job:', error)
      alert('Failed to stop job')
    }
  }
  
  const handleDownload = async () => {
    if (!job) return
    
    try {
      const blob = await downloadCSV(jobId)
      downloadBlob(blob, `${job.query.replace(/\s+/g, '_')}_${jobId}.csv`)
    } catch (error) {
      console.error('Failed to download CSV:', error)
      alert('Failed to download results')
    }
  }
  
  const getLogColor = (log: string) => {
    if (log.includes('Found:') || log.includes('@')) return 'text-green-400'
    if (log.toLowerCase().includes('error')) return 'text-red-400'
    if (log.toLowerCase().includes('rotating') || log.toLowerCase().includes('vpn')) return 'text-brand'
    return 'text-zinc-500'
  }
  
  if (!job) {
    return (
      <div className="flex items-center justify-center min-h-[calc(100vh-4rem)]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-brand"></div>
      </div>
    )
  }
  
  const MAX_PAGES = 500
  const progress = Math.min((job.stats.pages_crawled / MAX_PAGES) * 100, 100)
  
  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex items-start justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-zinc-50 mb-2">{job.query}</h1>
          <div className="flex items-center gap-3">
            <StatusBadge status={job.status} />
            <Badge variant="outline">{job.engine}</Badge>
            <Badge variant="outline">{job.backend}</Badge>
            {job.started_at && (
              <span className="text-sm text-zinc-400">
                Started {formatDate(job.started_at)}
              </span>
            )}
          </div>
        </div>
        
        {job.status === 'running' && (
          <Button variant="destructive" onClick={handleStop}>
            <StopCircle className="mr-2 h-4 w-4" />
            Stop Job
          </Button>
        )}
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-6">
          <div className="text-sm text-zinc-400 mb-1">Pages Crawled</div>
          <div className="text-3xl font-bold text-zinc-50">{job.stats.pages_crawled}</div>
        </div>
        
        <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-6">
          <div className="text-sm text-zinc-400 mb-1">Emails Found</div>
          <div className="text-3xl font-bold text-brand">{job.stats.total_emails}</div>
        </div>
        
        <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-6">
          <div className="text-sm text-zinc-400 mb-1">Rate/min</div>
          <div className="text-3xl font-bold text-zinc-50">
            {job.stats.rate_per_min.toFixed(1)}
          </div>
        </div>
        
        <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-6">
          <div className="text-sm text-zinc-400 mb-1">Errors</div>
          <div className={cn(
            'text-3xl font-bold',
            job.stats.errors > 0 ? 'text-red-500' : 'text-zinc-50'
          )}>
            {job.stats.errors}
          </div>
        </div>
      </div>
      
      {job.status === 'running' && (
        <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-6 mb-8">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-zinc-400">Progress</span>
            <span className="text-sm text-zinc-400">
              {job.stats.pages_crawled} / {MAX_PAGES}
            </span>
          </div>
          <div className="w-full h-2 bg-zinc-800 rounded-full overflow-hidden">
            <div
              className="h-full bg-brand transition-all duration-500 ease-out"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      )}
      
      <div className="rounded-lg border border-zinc-800 bg-zinc-900 mb-8">
        <div className="flex items-center justify-between p-4 border-b border-zinc-800">
          <div className="flex items-center gap-2">
            <h2 className="text-lg font-semibold text-zinc-50">Live Log</h2>
            {isLive && (
              <Badge variant="brand" className="animate-pulse">LIVE</Badge>
            )}
            {!isLive && job.status === 'completed' && (
              <Badge variant="secondary">ENDED</Badge>
            )}
          </div>
        </div>
        
        <div className="h-96 overflow-y-auto p-4 font-mono text-sm">
          {logs.length === 0 && (
            <div className="text-zinc-500 text-center py-12">
              Waiting for logs...
            </div>
          )}
          
          {logs.map((log, i) => (
            <div key={i} className={cn('mb-1', getLogColor(log))}>
              {log}
            </div>
          ))}
          
          <div ref={logsEndRef} />
        </div>
      </div>
      
      <div className="flex items-center gap-4">
        <Link href={`/jobs/${jobId}/results`}>
          <Button
            disabled={job.stats.total_emails === 0}
            size="lg"
          >
            <Eye className="mr-2 h-4 w-4" />
            View Results ({job.stats.total_emails})
          </Button>
        </Link>
        
        <Button
          variant="outline"
          onClick={handleDownload}
          disabled={job.stats.total_emails === 0}
          size="lg"
        >
          <Download className="mr-2 h-4 w-4" />
          Download CSV
        </Button>
      </div>
    </div>
  )
}
