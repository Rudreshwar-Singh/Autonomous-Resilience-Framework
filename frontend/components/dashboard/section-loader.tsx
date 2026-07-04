'use client'

import { useEffect, useState, type ReactNode } from 'react'
import { cn } from '@/lib/utils'

interface SectionLoaderProps {
  children: ReactNode
  skeleton: ReactNode
  /** Simulated initial load delay in ms (UI demonstration only). */
  delay?: number
  className?: string
}

/**
 * Shows a skeleton placeholder on first mount, then smoothly fades in the
 * real content. This is a purely client-side loading demonstration — no
 * network requests, sockets, or backend calls are involved.
 */
export function SectionLoader({ children, skeleton, delay = 800, className }: SectionLoaderProps) {
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const timer = setTimeout(() => setLoading(false), delay)
    return () => clearTimeout(timer)
  }, [delay])

  if (loading) {
    return <div className={cn('h-full', className)}>{skeleton}</div>
  }

  return (
    <div className={cn('h-full animate-in fade-in-0 duration-500', className)}>{children}</div>
  )
}
