// frontend/src/hooks/useIntersectionObserver.ts

import { useEffect, useRef, useState } from 'react'

interface UseIntersectionObserverProps {
  threshold?: number
  rootMargin?: string
  triggerOnce?: boolean
}

export function useIntersectionObserver({
  threshold = 0,
  rootMargin = '0px',
  triggerOnce = false
}: UseIntersectionObserverProps = {}) {
  const [isIntersecting, setIsIntersecting] = useState(false)
  const [hasIntersected, setHasIntersected] = useState(false)
  const targetRef = useRef<HTMLElement>(null)

  useEffect(() => {
    const target = targetRef.current

    if (!target) return

    const observer = new IntersectionObserver(
      ([entry]) => {
        const isIntersecting = entry.isIntersecting

        setIsIntersecting(isIntersecting)

        if (isIntersecting && !hasIntersected) {
          setHasIntersected(true)

          if (triggerOnce) {
            observer.unobserve(target)
          }
        }
      },
      {
        threshold,
        rootMargin
      }
    )

    observer.observe(target)

    return () => {
      observer.unobserve(target)
    }
  }, [threshold, rootMargin, triggerOnce, hasIntersected])

  return {
    targetRef,
    isIntersecting,
    hasIntersected
  }
}

