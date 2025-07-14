// frontend/src/hooks/useClipboard.ts

import { useState, useCallback } from 'react'
import toast from 'react-hot-toast'

export function useClipboard() {
  const [hasCopied, setHasCopied] = useState(false)

  const copyToClipboard = useCallback(async (text: string) => {
    try {
      await navigator.clipboard.writeText(text)
      setHasCopied(true)
      toast.success('Copied to clipboard')

      setTimeout(() => {
        setHasCopied(false)
      }, 2000)
    } catch (error) {
      console.error('Failed to copy to clipboard:', error)
      toast.error('Failed to copy to clipboard')
    }
  }, [])

  return { copyToClipboard, hasCopied }
}