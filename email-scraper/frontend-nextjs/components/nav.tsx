'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useEffect, useState } from 'react'
import { checkHealth } from '@/lib/api'
import { cn } from '@/lib/utils'

export function Nav() {
  const pathname = usePathname()
  const [isHealthy, setIsHealthy] = useState(true)
  
  useEffect(() => {
    const checkBackend = async () => {
      try {
        await checkHealth()
        setIsHealthy(true)
      } catch {
        setIsHealthy(false)
      }
    }
    
    checkBackend()
    const interval = setInterval(checkBackend, 30000)
    
    return () => clearInterval(interval)
  }, [])
  
  const links = [
    { href: '/', label: 'New Scrape' },
    { href: '/dashboard', label: 'Dashboard' },
    { href: '/settings', label: 'Settings' },
  ]
  
  return (
    <nav className="sticky top-0 z-50 border-b border-zinc-800 bg-zinc-950/80 backdrop-blur-sm">
      <div className="container mx-auto flex h-16 items-center justify-between px-4">
        <div className="flex items-center gap-8">
          <Link href="/" className="text-xl font-bold text-brand">
            EmailScraper
          </Link>
          
          <div className="flex items-center gap-1">
            {links.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className={cn(
                  'rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                  pathname === link.href
                    ? 'bg-zinc-900 text-zinc-50'
                    : 'text-zinc-400 hover:text-zinc-50 hover:bg-zinc-900/50'
                )}
              >
                {link.label}
              </Link>
            ))}
          </div>
        </div>
        
        <div className="flex items-center gap-2">
          <div
            className={cn(
              'h-2 w-2 rounded-full',
              isHealthy ? 'bg-green-500' : 'bg-red-500'
            )}
            title={isHealthy ? 'Backend connected' : 'Backend disconnected'}
          />
          <span className="text-xs text-zinc-500">
            {isHealthy ? 'Connected' : 'Offline'}
          </span>
        </div>
      </div>
    </nav>
  )
}
