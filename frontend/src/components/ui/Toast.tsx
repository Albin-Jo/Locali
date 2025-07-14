// frontend/src/components/ui/Toast.tsx

import React from 'react'
import { X, Check, AlertTriangle, Info, AlertCircle } from 'lucide-react'
import { cn } from '@/lib/utils'

export type ToastType = 'success' | 'error' | 'warning' | 'info'

interface ToastProps {
  id: string
  type: ToastType
  title?: string
  message: string
  duration?: number
  onClose: (id: string) => void
}

const toastIcons = {
  success: Check,
  error: AlertCircle,
  warning: AlertTriangle,
  info: Info,
}

const toastStyles = {
  success: 'border-green-500/20 bg-green-500/10 text-green-400',
  error: 'border-red-500/20 bg-red-500/10 text-red-400',
  warning: 'border-yellow-500/20 bg-yellow-500/10 text-yellow-400',
  info: 'border-blue-500/20 bg-blue-500/10 text-blue-400',
}

export function Toast({ id, type, title, message, duration = 5000, onClose }: ToastProps) {
  const Icon = toastIcons[type]

  React.useEffect(() => {
    const timer = setTimeout(() => {
      onClose(id)
    }, duration)

    return () => clearTimeout(timer)
  }, [id, duration, onClose])

  return (
    <div
      className={cn(
        'flex items-start gap-3 p-4 border rounded-lg shadow-lg animate-slide-in',
        'bg-card border-border',
        toastStyles[type]
      )}
    >
      <Icon className="w-5 h-5 shrink-0 mt-0.5" />

      <div className="flex-1 min-w-0">
        {title && (
          <h4 className="font-medium text-foreground mb-1">{title}</h4>
        )}
        <p className="text-sm text-muted-foreground">{message}</p>
      </div>

      <button
        onClick={() => onClose(id)}
        className="text-muted-foreground hover:text-foreground transition-colors"
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  )
}

