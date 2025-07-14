import { useEffect } from 'react'
import { appActions } from '@/store'

export function useKeyboardShortcuts() {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Cmd/Ctrl + K for search
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        appActions.openSearch()
      }

      // Escape to close modals/overlays
      if (e.key === 'Escape') {
        appActions.closeSearch()
      }
    }

    // Listen for custom events from global script
    const handleOpenSearch = () => appActions.openSearch()
    const handleEscapeKey = () => appActions.closeSearch()

    document.addEventListener('keydown', handleKeyDown)
    window.addEventListener('open-search', handleOpenSearch)
    window.addEventListener('escape-key', handleEscapeKey)

    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      window.removeEventListener('open-search', handleOpenSearch)
      window.removeEventListener('escape-key', handleEscapeKey)
    }
  }, [])
}
