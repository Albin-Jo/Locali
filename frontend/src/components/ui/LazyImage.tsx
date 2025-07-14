// frontend/src/components/ui/LazyImage.tsx

import React, { useState, useRef, useEffect } from 'react'
import { cn } from '@/lib/utils'

interface LazyImageProps extends React.ImgHTMLAttributes<HTMLImageElement> {
  src: string
  fallback?: string
  placeholder?: React.ReactNode
  className?: string
}

export function LazyImage({
  src,
  fallback,
  placeholder,
  className,
  ...props
}: LazyImageProps) {
  const [isLoaded, setIsLoaded] = useState(false)
  const [hasError, setHasError] = useState(false)
  const [isInView, setIsInView] = useState(false)
  const imgRef = useRef<HTMLImageElement>(null)

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsInView(true)
          observer.disconnect()
        }
      },
      { threshold: 0.1 }
    )

    if (imgRef.current) {
      observer.observe(imgRef.current)
    }

    return () => observer.disconnect()
  }, [])

  const handleLoad = () => {
    setIsLoaded(true)
    setHasError(false)
  }

  const handleError = () => {
    setHasError(true)
    setIsLoaded(false)
  }

  return (
    <div ref={imgRef} className={cn('relative overflow-hidden', className)}>
      {!isInView && placeholder && (
        <div className="absolute inset-0 flex items-center justify-center bg-muted">
          {placeholder}
        </div>
      )}

      {isInView && (
        <>
          <img
            src={hasError ? fallback : src}
            onLoad={handleLoad}
            onError={handleError}
            className={cn(
              'transition-opacity duration-300',
              isLoaded ? 'opacity-100' : 'opacity-0',
              className
            )}
            {...props}
          />

          {!isLoaded && !hasError && placeholder && (
            <div className="absolute inset-0 flex items-center justify-center bg-muted">
              {placeholder}
            </div>
          )}
        </>
      )}
    </div>
  )
}

