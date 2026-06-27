'use client'

import { useState, KeyboardEvent } from 'react'
import { useRouter } from 'next/navigation'
import useSWR from 'swr'
import { createJob, getJobs } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Checkbox } from '@/components/ui/checkbox'
import { JobCard } from '@/components/job-card'
import { X } from 'lucide-react'
import { cn } from '@/lib/utils'

export default function HomePage() {
  const router = useRouter()
  const { data: jobsData } = useSWR('/jobs', getJobs, { refreshInterval: 5000 })
  
  const [query, setQuery] = useState('')
  const [engine, setEngine] = useState<'google' | 'ddg'>('google')
  const [backend, setBackend] = useState<'scrapling' | 'playwright'>('scrapling')
  const [checkMx, setCheckMx] = useState(true)
  const [vpnEnabled, setVpnEnabled] = useState(false)
  const [expandLocations, setExpandLocations] = useState(false)
  const [locations, setLocations] = useState<string[]>([])
  const [locationInput, setLocationInput] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  
  const handleLocationKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && locationInput.trim()) {
      e.preventDefault()
      if (!locations.includes(locationInput.trim())) {
        setLocations([...locations, locationInput.trim()])
      }
      setLocationInput('')
    }
  }
  
  const removeLocation = (location: string) => {
    setLocations(locations.filter((l) => l !== location))
  }
  
  const handleSubmit = async () => {
    if (!query.trim() || isSubmitting) return
    
    setIsSubmitting(true)
    
    try {
      const job = await createJob({
        query: query.trim(),
        engine,
        backend,
        check_mx: checkMx,
        expand_locations: expandLocations,
        locations: expandLocations ? locations : undefined,
      })
      
      router.push(`/jobs/${job.id}`)
    } catch (error) {
      console.error('Failed to create job:', error)
      alert('Failed to start scraping job')
    } finally {
      setIsSubmitting(false)
    }
  }
  
  const recentJobs = jobsData?.jobs?.slice(0, 5) || []
  
  return (
    <div className="container mx-auto max-w-2xl px-4 py-12">
      <div className="mb-12 text-center">
        <h1 className="text-4xl font-bold text-zinc-50 mb-3">
          Email Scraper
        </h1>
        <p className="text-zinc-400">
          Search, crawl, and extract emails at scale
        </p>
      </div>
      
      <div className="space-y-6 rounded-lg border border-zinc-800 bg-zinc-900 p-6">
        <div>
          <label htmlFor="query" className="block text-sm font-medium text-zinc-300 mb-2">
            Search Query
          </label>
          <Input
            id="query"
            type="text"
            placeholder="e.g., dental clinics london"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
            className="text-lg h-12"
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-zinc-300 mb-3">
            Search Engine
          </label>
          <div className="flex gap-2">
            {(['google', 'ddg'] as const).map((option) => (
              <button
                key={option}
                type="button"
                onClick={() => setEngine(option)}
                className={cn(
                  'flex-1 rounded-lg border px-4 py-2 text-sm font-medium transition-colors',
                  engine === option
                    ? 'border-brand bg-brand/10 text-brand'
                    : 'border-zinc-800 text-zinc-400 hover:border-zinc-700 hover:text-zinc-300'
                )}
              >
                {option === 'google' ? 'Google' : 'DuckDuckGo'}
              </button>
            ))}
          </div>
        </div>
        
        <div>
          <label className="block text-sm font-medium text-zinc-300 mb-3">
            Backend
          </label>
          <div className="flex gap-2">
            {(['scrapling', 'playwright'] as const).map((option) => (
              <button
                key={option}
                type="button"
                onClick={() => setBackend(option)}
                className={cn(
                  'flex-1 rounded-lg border px-4 py-2 text-sm font-medium transition-colors capitalize',
                  backend === option
                    ? 'border-brand bg-brand/10 text-brand'
                    : 'border-zinc-800 text-zinc-400 hover:border-zinc-700 hover:text-zinc-300'
                )}
              >
                {option}
              </button>
            ))}
          </div>
        </div>
        
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <Checkbox
              id="check-mx"
              checked={checkMx}
              onCheckedChange={(checked) => setCheckMx(checked === true)}
            />
            <label htmlFor="check-mx" className="text-sm text-zinc-300 cursor-pointer">
              MX Validation
            </label>
          </div>
          
          <div className="flex items-center gap-2">
            <Checkbox
              id="vpn-enabled"
              checked={vpnEnabled}
              onCheckedChange={(checked) => setVpnEnabled(checked === true)}
            />
            <label htmlFor="vpn-enabled" className="text-sm text-zinc-300 cursor-pointer">
              VPN Rotation
            </label>
          </div>
          
          <div className="flex items-center gap-2">
            <Checkbox
              id="expand-locations"
              checked={expandLocations}
              onCheckedChange={(checked) => setExpandLocations(checked === true)}
            />
            <label htmlFor="expand-locations" className="text-sm text-zinc-300 cursor-pointer">
              Expand Locations
            </label>
          </div>
        </div>
        
        {expandLocations && (
          <div>
            <label htmlFor="locations" className="block text-sm font-medium text-zinc-300 mb-2">
              Locations
            </label>
            <Input
              id="locations"
              type="text"
              placeholder="Type location and press Enter"
              value={locationInput}
              onChange={(e) => setLocationInput(e.target.value)}
              onKeyDown={handleLocationKeyDown}
            />
            {locations.length > 0 && (
              <div className="flex flex-wrap gap-2 mt-3">
                {locations.map((location) => (
                  <button
                    key={location}
                    type="button"
                    onClick={() => removeLocation(location)}
                    className="inline-flex items-center gap-1.5 rounded-full bg-brand/10 border border-brand/20 px-3 py-1 text-sm text-brand hover:bg-brand/20 transition-colors"
                  >
                    {location}
                    <X className="h-3 w-3" />
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
        
        <Button
          onClick={handleSubmit}
          disabled={!query.trim() || isSubmitting}
          className="w-full h-12 text-base"
        >
          {isSubmitting ? 'Starting...' : 'Start Scraping'}
        </Button>
      </div>
      
      {recentJobs.length > 0 && (
        <div className="mt-12">
          <h2 className="text-lg font-semibold text-zinc-50 mb-4">Recent Jobs</h2>
          <div className="space-y-3">
            {recentJobs.map((job) => (
              <JobCard key={job.id} job={job} />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
