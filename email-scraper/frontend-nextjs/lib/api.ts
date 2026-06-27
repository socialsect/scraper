const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export interface JobParams {
  query: string
  engine?: 'google' | 'ddg'
  backend?: 'scrapling' | 'playwright'
  expand_locations?: boolean
  locations?: string[]
  check_mx?: boolean
  output_file?: string
}

export interface JobStats {
  query: string
  backend: string
  elapsed_seconds: number
  pages_crawled: number
  new_emails: number
  total_emails: number
  last_email: string
  queue_size: number
  errors: number
  rate_per_min: number
}

export interface Job {
  id: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'stopped'
  query: string
  engine: string
  backend: string
  created_at: string
  started_at?: string
  completed_at?: string
  error?: string
  stats: JobStats
}

export interface Config {
  [key: string]: any
}

export async function createJob(params: JobParams): Promise<Job> {
  const response = await fetch(`${API_URL}/jobs`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  })
  
  if (!response.ok) {
    throw new Error(`Failed to create job: ${response.statusText}`)
  }
  
  return response.json()
}

export async function getJobs(): Promise<{ jobs: Job[] }> {
  const response = await fetch(`${API_URL}/jobs`)
  
  if (!response.ok) {
    throw new Error(`Failed to fetch jobs: ${response.statusText}`)
  }
  
  return response.json()
}

export async function getJobStatus(id: string): Promise<Job> {
  const response = await fetch(`${API_URL}/jobs/${id}/status`)
  
  if (!response.ok) {
    throw new Error(`Failed to fetch job status: ${response.statusText}`)
  }
  
  return response.json()
}

export async function getJobLogs(id: string): Promise<{ logs: string[] }> {
  const response = await fetch(`${API_URL}/jobs/${id}/logs`)
  
  if (!response.ok) {
    throw new Error(`Failed to fetch job logs: ${response.statusText}`)
  }
  
  return response.json()
}

export async function stopJob(id: string): Promise<{ status: string }> {
  const response = await fetch(`${API_URL}/jobs/${id}`, {
    method: 'DELETE',
  })
  
  if (!response.ok) {
    throw new Error(`Failed to stop job: ${response.statusText}`)
  }
  
  return response.json()
}

export async function downloadCSV(id: string): Promise<Blob> {
  const response = await fetch(`${API_URL}/jobs/${id}/download`)
  
  if (!response.ok) {
    throw new Error(`Failed to download CSV: ${response.statusText}`)
  }
  
  return response.blob()
}

export async function getConfig(): Promise<Config> {
  const response = await fetch(`${API_URL}/api/config`)
  
  if (!response.ok) {
    throw new Error(`Failed to fetch config: ${response.statusText}`)
  }
  
  return response.json()
}

export async function updateConfig(config: Config): Promise<Config> {
  const response = await fetch(`${API_URL}/api/config`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  })
  
  if (!response.ok) {
    throw new Error(`Failed to update config: ${response.statusText}`)
  }
  
  return response.json()
}

export function streamJob(
  id: string,
  onData: (data: any) => void,
  onDone: () => void,
  onError?: (error: Error) => void
): () => void {
  const eventSource = new EventSource(`${API_URL}/jobs/${id}/stream`)
  
  eventSource.onmessage = (event) => {
    if (event.data === 'ping') {
      return
    }
    
    try {
      const data = JSON.parse(event.data)
      
      if (data._done) {
        eventSource.close()
        onDone()
      } else {
        onData(data)
      }
    } catch (error) {
      console.error('Failed to parse SSE data:', error)
    }
  }
  
  eventSource.onerror = (error) => {
    console.error('SSE error:', error)
    eventSource.close()
    if (onError) {
      onError(new Error('Stream connection failed'))
    }
  }
  
  return () => eventSource.close()
}

export async function checkHealth(): Promise<{ status: string; database: string }> {
  const response = await fetch(`${API_URL}/health`)
  
  if (!response.ok) {
    throw new Error('Backend unreachable')
  }
  
  return response.json()
}
