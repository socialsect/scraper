'use client'

import { useState, useMemo } from 'react'
import useSWR from 'swr'
import { getJobs, stopJob, downloadCSV } from '@/lib/api'
import { StatusBadge } from '@/components/status-badge'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { formatDate, formatDuration, downloadBlob } from '@/lib/utils'
import Link from 'next/link'
import { Download, Eye, StopCircle, Trash2 } from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { format, subDays, startOfDay } from 'date-fns'

export default function DashboardPage() {
  const { data: jobsData, mutate } = useSWR('/jobs', getJobs, { refreshInterval: 3000 })
  const [filter, setFilter] = useState<'all' | 'running' | 'completed' | 'failed'>('all')
  const [searchQuery, setSearchQuery] = useState('')
  
  const jobs = jobsData?.jobs || []
  
  const stats = useMemo(() => {
    const totalEmails = jobs.reduce((sum, job) => sum + (job.stats?.total_emails || 0), 0)
    const totalJobs = jobs.length
    const completedJobs = jobs.filter(j => j.status === 'completed').length
    const domainsSet = new Set<string>()
    
    jobs.forEach(job => {
      if (job.stats?.total_emails > 0) {
        domainsSet.add(job.query)
      }
    })
    
    const successRate = totalJobs > 0 ? ((completedJobs / totalJobs) * 100).toFixed(1) : '0'
    
    return {
      totalEmails,
      totalJobs,
      domains: domainsSet.size,
      successRate: `${successRate}%`,
    }
  }, [jobs])
  
  const chartData = useMemo(() => {
    const last14Days = Array.from({ length: 14 }, (_, i) => {
      const date = startOfDay(subDays(new Date(), 13 - i))
      return {
        date: format(date, 'MMM dd'),
        emails: 0,
      }
    })
    
    jobs.forEach(job => {
      if (job.completed_at && job.stats?.total_emails > 0) {
        const jobDate = format(startOfDay(new Date(job.completed_at)), 'MMM dd')
        const dayData = last14Days.find(d => d.date === jobDate)
        if (dayData) {
          dayData.emails += job.stats.total_emails
        }
      }
    })
    
    return last14Days
  }, [jobs])
  
  const filteredJobs = useMemo(() => {
    let filtered = jobs
    
    if (filter !== 'all') {
      filtered = filtered.filter(job => job.status === filter)
    }
    
    if (searchQuery) {
      filtered = filtered.filter(job =>
        job.query.toLowerCase().includes(searchQuery.toLowerCase())
      )
    }
    
    return filtered
  }, [jobs, filter, searchQuery])
  
  const handleStopJob = async (jobId: string) => {
    try {
      await stopJob(jobId)
      mutate()
    } catch (error) {
      console.error('Failed to stop job:', error)
      alert('Failed to stop job')
    }
  }
  
  const handleDownload = async (jobId: string, query: string) => {
    try {
      const blob = await downloadCSV(jobId)
      downloadBlob(blob, `${query.replace(/\s+/g, '_')}_${jobId}.csv`)
    } catch (error) {
      console.error('Failed to download CSV:', error)
      alert('Failed to download results')
    }
  }
  
  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold text-zinc-50 mb-8">Dashboard</h1>
      
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-6">
          <div className="text-sm text-zinc-400 mb-1">Total Emails</div>
          <div className="text-3xl font-bold text-brand">{stats.totalEmails.toLocaleString()}</div>
        </div>
        
        <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-6">
          <div className="text-sm text-zinc-400 mb-1">Total Jobs</div>
          <div className="text-3xl font-bold text-zinc-50">{stats.totalJobs}</div>
        </div>
        
        <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-6">
          <div className="text-sm text-zinc-400 mb-1">Domains Scraped</div>
          <div className="text-3xl font-bold text-zinc-50">{stats.domains}</div>
        </div>
        
        <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-6">
          <div className="text-sm text-zinc-400 mb-1">Success Rate</div>
          <div className="text-3xl font-bold text-green-500">{stats.successRate}</div>
        </div>
      </div>
      
      <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-6 mb-8">
        <h2 className="text-lg font-semibold text-zinc-50 mb-4">Emails Found (Last 14 Days)</h2>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
            <XAxis dataKey="date" stroke="#71717a" style={{ fontSize: '12px' }} />
            <YAxis stroke="#71717a" style={{ fontSize: '12px' }} />
            <Tooltip
              contentStyle={{
                backgroundColor: '#18181b',
                border: '1px solid #27272a',
                borderRadius: '0.5rem',
                color: '#fafafa',
              }}
            />
            <Line
              type="monotone"
              dataKey="emails"
              stroke="#695af2"
              strokeWidth={2}
              dot={{ fill: '#695af2', r: 4 }}
              activeDot={{ r: 6 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
      
      <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-semibold text-zinc-50">All Jobs</h2>
          
          <div className="flex items-center gap-4">
            <Input
              type="text"
              placeholder="Search jobs..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-64"
            />
            
            <div className="flex gap-2">
              {(['all', 'running', 'completed', 'failed'] as const).map((filterOption) => (
                <Button
                  key={filterOption}
                  variant={filter === filterOption ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setFilter(filterOption)}
                  className="capitalize"
                >
                  {filterOption}
                </Button>
              ))}
            </div>
          </div>
        </div>
        
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-zinc-800 text-left text-sm text-zinc-400">
                <th className="pb-3 font-medium">Query</th>
                <th className="pb-3 font-medium">Engine</th>
                <th className="pb-3 font-medium">Backend</th>
                <th className="pb-3 font-medium">Status</th>
                <th className="pb-3 font-medium text-right">Emails</th>
                <th className="pb-3 font-medium">Started</th>
                <th className="pb-3 font-medium">Duration</th>
                <th className="pb-3 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="text-sm">
              {filteredJobs.map((job) => {
                const duration = job.started_at && job.completed_at
                  ? Math.floor((new Date(job.completed_at).getTime() - new Date(job.started_at).getTime()) / 1000)
                  : job.stats?.elapsed_seconds || 0
                
                return (
                  <tr key={job.id} className="border-b border-zinc-800 last:border-0">
                    <td className="py-4 max-w-xs truncate text-zinc-50">{job.query}</td>
                    <td className="py-4">
                      <Badge variant="outline" className="text-xs">{job.engine}</Badge>
                    </td>
                    <td className="py-4">
                      <Badge variant="outline" className="text-xs">{job.backend}</Badge>
                    </td>
                    <td className="py-4">
                      <StatusBadge status={job.status} />
                    </td>
                    <td className="py-4 text-right text-brand font-medium">
                      {job.stats?.total_emails || 0}
                    </td>
                    <td className="py-4 text-zinc-400">
                      {job.started_at ? formatDate(job.started_at) : '—'}
                    </td>
                    <td className="py-4 text-zinc-400">
                      {duration > 0 ? formatDuration(duration) : '—'}
                    </td>
                    <td className="py-4">
                      <div className="flex items-center justify-end gap-2">
                        <Link href={`/jobs/${job.id}`}>
                          <Button variant="ghost" size="icon" title="View">
                            <Eye className="h-4 w-4" />
                          </Button>
                        </Link>
                        
                        {job.stats?.total_emails > 0 && (
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleDownload(job.id, job.query)}
                            title="Download CSV"
                          >
                            <Download className="h-4 w-4" />
                          </Button>
                        )}
                        
                        {job.status === 'running' && (
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleStopJob(job.id)}
                            title="Stop Job"
                          >
                            <StopCircle className="h-4 w-4 text-red-500" />
                          </Button>
                        )}
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
          
          {filteredJobs.length === 0 && (
            <div className="text-center py-12 text-zinc-500">
              No jobs found
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
