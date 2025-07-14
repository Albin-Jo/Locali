// frontend/src/components/system/StatusIndicator.tsx

import React from 'react'
import { type LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'

interface StatusIndicatorProps {
  icon: LucideIcon
  status: 'good' | 'warning' | 'error' | 'offline' | 'online'
  tooltip?: string
  className?: string
}

export function StatusIndicator({
  icon: Icon,
  status,
  tooltip,
  className
}: StatusIndicatorProps) {
  const statusColors = {
    good: 'text-green-500',
    warning: 'text-yellow-500',
    error: 'text-red-500',
    offline: 'text-gray-500',
    online: 'text-green-500',
  }

  return (
    <div
      className={cn('flex items-center gap-1', className)}
      title={tooltip}
    >
      <Icon className={cn('w-4 h-4', statusColors[status])} />
      <div className={cn('w-2 h-2 rounded-full', {
        'bg-green-500': status === 'good' || status === 'online',
        'bg-yellow-500': status === 'warning',
        'bg-red-500': status === 'error',
        'bg-gray-500': status === 'offline',
      })} />
    </div>
  )
}