// frontend/src/hooks/usePerformanceMonitor.ts

import { useEffect, useRef } from 'react'

interface PerformanceMetrics {
  renderTime: number
  componentName: string
  timestamp: number
}

export function usePerformanceMonitor(componentName: string) {
  const startTimeRef = useRef<number>()
  const metricsRef = useRef<PerformanceMetrics[]>([])

  useEffect(() => {
    startTimeRef.current = performance.now()

    return () => {
      if (startTimeRef.current) {
        const renderTime = performance.now() - startTimeRef.current

        const metric: PerformanceMetrics = {
          renderTime,
          componentName,
          timestamp: Date.now()
        }

        metricsRef.current.push(metric)

        // Log slow renders in development
        if (process.env.NODE_ENV === 'development' && renderTime > 16) {
          console.warn(`Slow render detected in ${componentName}: ${renderTime.toFixed(2)}ms`)
        }

        // Keep only last 100 metrics
        if (metricsRef.current.length > 100) {
          metricsRef.current = metricsRef.current.slice(-100)
        }
      }
    }
  })

  const getMetrics = () => metricsRef.current

  const getAverageRenderTime = () => {
    const metrics = metricsRef.current
    if (metrics.length === 0) return 0

    const total = metrics.reduce((sum, metric) => sum + metric.renderTime, 0)
    return total / metrics.length
  }

  return {
    getMetrics,
    getAverageRenderTime
  }
}