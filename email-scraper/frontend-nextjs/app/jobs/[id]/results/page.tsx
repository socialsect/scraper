'use client'

import { useState, useMemo } from 'react'
import { useParams } from 'next/navigation'
import { downloadCSV, getJobStatus } from '@/lib/api'
import { downloadBlob, copyToClipboard, extractDomain } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Checkbox } from '@/components/ui/checkbox'
import { Badge } from '@/components/ui/badge'
import { Download, Copy, ExternalLink, ChevronLeft, ChevronRight } from 'lucide-react'
import { cn } from '@/lib/utils'
import useSWR from 'swr'

interface EmailResult {
  email: string
  source: string
  phone: string
  linkedin: string
  twitter: string
  instagram: string
  facebook: string
  youtube: string
  mx_valid: string
  confidence: string
}

export default function ResultsPage() {
  const params = useParams()
  const jobId = params.id as string
  
  const { data: job } = useSWR(
    jobId ? `/jobs/${jobId}/status` : null,
    () => getJobStatus(jobId)
  )
  
  const [results, setResults] = useState<EmailResult[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [hasPhone, setHasPhone] = useState(false)
  const [hasLinkedIn, setHasLinkedIn] = useState(false)
  const [hasTwitter, setHasTwitter] = useState(false)
  const [mxValid, setMxValid] = useState(false)
  const [confidenceFilter, setConfidenceFilter] = useState<'all' | '3' | '2' | '1'>('all')
  const [selectedEmails, setSelectedEmails] = useState<Set<string>>(new Set())
  const [page, setPage] = useState(1)
  const [domainPanel, setDomainPanel] = useState<string | null>(null)
  const perPage = 50
  
  useSWR(
    jobId ? `/jobs/${jobId}/download` : null,
    async () => {
      const blob = await downloadCSV(jobId)
      const text = await blob.text()
      const lines = text.split('\n')
      const headers = lines[0].split(',')
      
      const parsed: EmailResult[] = []
      for (let i = 1; i < lines.length; i++) {
        if (!lines[i].trim()) continue
        const values = lines[i].split(',')
        if (values.length >= headers.length) {
          parsed.push({
            email: values[0] || '',
            source: values[1] || '',
            phone: values[2] || '',
            linkedin: values[3] || '',
            twitter: values[4] || '',
            instagram: values[5] || '',
            facebook: values[6] || '',
            youtube: values[7] || '',
            mx_valid: values[8] || '',
            confidence: values[9] || '1',
          })
        }
      }
      
      setResults(parsed)
      setIsLoading(false)
      return parsed
    }
  )
  
  const filteredResults = useMemo(() => {
    let filtered = results
    
    if (searchQuery) {
      const query = searchQuery.toLowerCase()
      filtered = filtered.filter(r =>
        r.email.toLowerCase().includes(query) ||
        extractDomain(r.source).toLowerCase().includes(query)
      )
    }
    
    if (hasPhone) filtered = filtered.filter(r => r.phone)
    if (hasLinkedIn) filtered = filtered.filter(r => r.linkedin)
    if (hasTwitter) filtered = filtered.filter(r => r.twitter)
    if (mxValid) filtered = filtered.filter(r => r.mx_valid === 'yes')
    if (confidenceFilter !== 'all') {
      filtered = filtered.filter(r => r.confidence === confidenceFilter)
    }
    
    return filtered
  }, [results, searchQuery, hasPhone, hasLinkedIn, hasTwitter, mxValid, confidenceFilter])
  
  const activeFiltersCount = [
    hasPhone,
    hasLinkedIn,
    hasTwitter,
    mxValid,
    confidenceFilter !== 'all',
  ].filter(Boolean).length
  
  const paginatedResults = useMemo(() => {
    const start = (page - 1) * perPage
    return filteredResults.slice(start, start + perPage)
  }, [filteredResults, page])
  
  const totalPages = Math.ceil(filteredResults.length / perPage)
  
  const handleDownloadCSV = async () => {
    try {
      const blob = await downloadCSV(jobId)
      downloadBlob(blob, `results_${jobId}.csv`)
    } catch (error) {
      console.error('Failed to download CSV:', error)
      alert('Failed to download CSV')
    }
  }
  
  const handleDownloadJSON = () => {
    const json = JSON.stringify(filteredResults, null, 2)
    const blob = new Blob([json], { type: 'application/json' })
    downloadBlob(blob, `results_${jobId}.json`)
  }
  
  const handleCopyAllEmails = async () => {
    const emails = filteredResults.map(r => r.email).join('\n')
    try {
      await copyToClipboard(emails)
      alert('Copied to clipboard')
    } catch (error) {
      console.error('Failed to copy:', error)
      alert('Failed to copy to clipboard')
    }
  }
  
  const handleCopyEmail = async (email: string) => {
    try {
      await copyToClipboard(email)
    } catch (error) {
      console.error('Failed to copy:', error)
    }
  }
  
  const toggleSelectAll = () => {
    if (selectedEmails.size === paginatedResults.length) {
      setSelectedEmails(new Set())
    } else {
      setSelectedEmails(new Set(paginatedResults.map(r => r.email)))
    }
  }
  
  const toggleSelect = (email: string) => {
    const newSet = new Set(selectedEmails)
    if (newSet.has(email)) {
      newSet.delete(email)
    } else {
      newSet.add(email)
    }
    setSelectedEmails(newSet)
  }
  
  const getConfidenceBadge = (confidence: string) => {
    const configs = {
      '3': { color: 'text-green-400', bg: 'bg-green-900/20', label: 'High', dot: 'bg-green-500' },
      '2': { color: 'text-yellow-400', bg: 'bg-yellow-900/20', label: 'Med', dot: 'bg-yellow-500' },
      '1': { color: 'text-red-400', bg: 'bg-red-900/20', label: 'Low', dot: 'bg-red-500' },
    }
    
    const config = configs[confidence as '1' | '2' | '3'] || configs['1']
    
    return (
      <div className={cn('inline-flex items-center gap-1.5 px-2 py-1 rounded text-xs', config.color, config.bg)}>
        <div className={cn('w-1.5 h-1.5 rounded-full', config.dot)} />
        {config.label}
      </div>
    )
  }
  
  const domainEmails = useMemo(() => {
    if (!domainPanel) return []
    return results.filter(r => extractDomain(r.source) === domainPanel)
  }, [results, domainPanel])
  
  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[calc(100vh-4rem)]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-brand"></div>
      </div>
    )
  }
  
  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex items-start justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-zinc-50 mb-2">Results</h1>
          {job && (
            <p className="text-zinc-400">
              {job.query} · <span className="text-brand font-medium">{results.length}</span> emails
            </p>
          )}
        </div>
        
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={handleDownloadCSV}>
            <Download className="mr-2 h-4 w-4" />
            CSV
          </Button>
          
          <Button variant="outline" onClick={handleDownloadJSON}>
            <Download className="mr-2 h-4 w-4" />
            JSON
          </Button>
          
          <Button variant="outline" onClick={handleCopyAllEmails}>
            <Copy className="mr-2 h-4 w-4" />
            Copy All
          </Button>
        </div>
      </div>
      
      <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-4 mb-6">
        <div className="flex flex-wrap items-center gap-4">
          <Input
            type="text"
            placeholder="Search email or domain..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="flex-1 min-w-[200px]"
          />
          
          <div className="flex items-center gap-3 flex-wrap">
            <label className="flex items-center gap-2 text-sm text-zinc-300 cursor-pointer">
              <Checkbox checked={hasPhone} onCheckedChange={(c) => setHasPhone(c === true)} />
              Has Phone
            </label>
            
            <label className="flex items-center gap-2 text-sm text-zinc-300 cursor-pointer">
              <Checkbox checked={hasLinkedIn} onCheckedChange={(c) => setHasLinkedIn(c === true)} />
              Has LinkedIn
            </label>
            
            <label className="flex items-center gap-2 text-sm text-zinc-300 cursor-pointer">
              <Checkbox checked={hasTwitter} onCheckedChange={(c) => setHasTwitter(c === true)} />
              Has Twitter
            </label>
            
            <label className="flex items-center gap-2 text-sm text-zinc-300 cursor-pointer">
              <Checkbox checked={mxValid} onCheckedChange={(c) => setMxValid(c === true)} />
              MX Valid
            </label>
          </div>
          
          <div className="flex items-center gap-2">
            <span className="text-sm text-zinc-400">Confidence:</span>
            {(['all', '3', '2', '1'] as const).map((conf) => (
              <Button
                key={conf}
                variant={confidenceFilter === conf ? 'default' : 'outline'}
                size="sm"
                onClick={() => setConfidenceFilter(conf)}
              >
                {conf === 'all' ? 'All' : conf === '3' ? 'High' : conf === '2' ? 'Med' : 'Low'}
              </Button>
            ))}
          </div>
          
          {activeFiltersCount > 0 && (
            <Badge variant="brand">{activeFiltersCount} filters active</Badge>
          )}
        </div>
      </div>
      
      <div className="rounded-lg border border-zinc-800 bg-zinc-900 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-zinc-800 text-left text-sm text-zinc-400">
                <th className="p-3 w-12">
                  <Checkbox
                    checked={selectedEmails.size === paginatedResults.length && paginatedResults.length > 0}
                    onCheckedChange={toggleSelectAll}
                  />
                </th>
                <th className="p-3 font-medium">Email</th>
                <th className="p-3 font-medium">Domain</th>
                <th className="p-3 font-medium">Phone</th>
                <th className="p-3 font-medium">LinkedIn</th>
                <th className="p-3 font-medium">Confidence</th>
                <th className="p-3 font-medium">Source</th>
                <th className="p-3 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="text-sm">
              {paginatedResults.map((result) => {
                const domain = extractDomain(result.source)
                
                return (
                  <tr key={result.email} className="border-b border-zinc-800 last:border-0 hover:bg-zinc-800/50">
                    <td className="p-3">
                      <Checkbox
                        checked={selectedEmails.has(result.email)}
                        onCheckedChange={() => toggleSelect(result.email)}
                      />
                    </td>
                    <td className="p-3 font-mono text-zinc-50">{result.email}</td>
                    <td className="p-3">
                      <button
                        onClick={() => setDomainPanel(domain)}
                        className="text-brand hover:underline"
                      >
                        {domain}
                      </button>
                    </td>
                    <td className="p-3 text-zinc-400">{result.phone || '—'}</td>
                    <td className="p-3">
                      {result.linkedin ? (
                        <a
                          href={result.linkedin}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-brand hover:underline"
                        >
                          ✓
                        </a>
                      ) : (
                        <span className="text-zinc-600">—</span>
                      )}
                    </td>
                    <td className="p-3">{getConfidenceBadge(result.confidence)}</td>
                    <td className="p-3 max-w-xs truncate">
                      <a
                        href={result.source}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-zinc-400 hover:text-zinc-300 text-xs"
                        title={result.source}
                      >
                        {result.source}
                      </a>
                    </td>
                    <td className="p-3">
                      <div className="flex items-center justify-end gap-2">
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleCopyEmail(result.email)}
                          title="Copy email"
                        >
                          <Copy className="h-4 w-4" />
                        </Button>
                        
                        <a
                          href={result.source}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          <Button variant="ghost" size="icon" title="Open source">
                            <ExternalLink className="h-4 w-4" />
                          </Button>
                        </a>
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
          
          {filteredResults.length === 0 && (
            <div className="text-center py-12 text-zinc-500">
              No results found
            </div>
          )}
        </div>
        
        {totalPages > 1 && (
          <div className="flex items-center justify-between border-t border-zinc-800 px-4 py-3">
            <div className="text-sm text-zinc-400">
              Showing {((page - 1) * perPage) + 1} to {Math.min(page * perPage, filteredResults.length)} of {filteredResults.length} results
            </div>
            
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
              
              <span className="text-sm text-zinc-300">
                Page {page} of {totalPages}
              </span>
              
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        )}
      </div>
      
      {domainPanel && (
        <div className="fixed right-0 top-16 bottom-0 w-96 bg-zinc-900 border-l border-zinc-800 shadow-2xl overflow-y-auto z-50">
          <div className="sticky top-0 bg-zinc-900 border-b border-zinc-800 p-4">
            <div className="flex items-start justify-between">
              <div>
                <h3 className="font-semibold text-zinc-50 mb-1">{domainPanel}</h3>
                <p className="text-sm text-zinc-400">{domainEmails.length} emails</p>
              </div>
              
              <Button variant="ghost" size="icon" onClick={() => setDomainPanel(null)}>
                ✕
              </Button>
            </div>
            
            <Button
              variant="outline"
              size="sm"
              className="w-full mt-3"
              onClick={() => {
                const emails = domainEmails.map(e => e.email).join('\n')
                copyToClipboard(emails)
                alert('Copied to clipboard')
              }}
            >
              <Copy className="mr-2 h-4 w-4" />
              Copy all from domain
            </Button>
          </div>
          
          <div className="p-4 space-y-3">
            {domainEmails.map((result) => (
              <div
                key={result.email}
                className="rounded-lg border border-zinc-800 bg-zinc-950 p-3 space-y-2"
              >
                <div className="font-mono text-sm text-zinc-50">{result.email}</div>
                
                {result.phone && (
                  <div className="text-xs text-zinc-400">📞 {result.phone}</div>
                )}
                
                <div className="flex items-center gap-2 flex-wrap">
                  {result.linkedin && (
                    <a
                      href={result.linkedin}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-brand hover:underline"
                    >
                      LinkedIn
                    </a>
                  )}
                  
                  {result.twitter && (
                    <a
                      href={result.twitter}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-brand hover:underline"
                    >
                      Twitter
                    </a>
                  )}
                  
                  {getConfidenceBadge(result.confidence)}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
