// frontend/src/components/search/SearchOverlay.tsx

import React, { useState, useEffect, useRef } from 'react'
import { Search, X, ArrowRight, File, MessageSquare, Hash } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { useSearch } from '@/lib/queries'
import { useAppStore, appActions } from '@/store'
import { debounce } from '@/lib/utils'
import { cn } from '@/lib/utils'

export function SearchOverlay() {
  const { search } = useAppStore()
  const [localQuery, setLocalQuery] = useState(search.query)
  const inputRef = useRef<HTMLInputElement>(null)
  const searchMutation = useSearch()

  // Debounced search
  const debouncedSearch = debounce((query: string) => {
    if (query.trim()) {
      searchMutation.mutate({
        query: query.trim(),
        max_results: 10,
      })
    }
  }, 300)

  useEffect(() => {
    debouncedSearch(localQuery)
  }, [localQuery, debouncedSearch])

  useEffect(() => {
    // Focus input when overlay opens
    if (search.isOpen && inputRef.current) {
      inputRef.current.focus()
    }
  }, [search.isOpen])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      appActions.closeSearch()
    }
  }

  if (!search.isOpen) return null

  return (
    <div className="fixed inset-0 bg-black/50 flex items-start justify-center pt-20 z-50">
      <div
        className="bg-popover border border-border rounded-lg w-full max-w-2xl shadow-xl animate-slide-in"
        onKeyDown={handleKeyDown}
      >
        {/* Search input */}
        <div className="p-4 border-b border-border">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-muted-foreground" />
            <Input
              ref={inputRef}
              value={localQuery}
              onChange={(e) => setLocalQuery(e.target.value)}
              placeholder="Search documents, conversations, and code..."
              className="pl-12 pr-12 h-12 text-base"
              autoFocus
            />
            <Button
              variant="ghost"
              size="sm"
              onClick={() => appActions.closeSearch()}
              className="absolute right-2 top-1/2 transform -translate-y-1/2 h-8 w-8 p-0"
            >
              <X className="w-4 h-4" />
            </Button>
          </div>

          {/* Search stats */}
          {search.results.length > 0 && (
            <div className="flex items-center justify-between mt-3 text-sm text-muted-foreground">
              <span>
                {search.results.length} result{search.results.length !== 1 ? 's' : ''}
                {localQuery && ` for "${localQuery}"`}
              </span>
              <span className="text-xs">
                Press ↑↓ to navigate, Enter to select, Esc to close
              </span>
            </div>
          )}
        </div>

        {/* Search results */}
        <div className="max-h-96 overflow-y-auto">
          {search.isSearching ? (
            <div className="p-8 text-center">
              <div className="inline-block w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
              <p className="mt-2 text-sm text-muted-foreground">Searching...</p>
            </div>
          ) : search.results.length > 0 ? (
            <div className="p-2">
              {search.results.map((result, index) => (
                <SearchResultItem
                  key={result.chunk_id}
                  result={result}
                  isSelected={index === 0} // TODO: Add keyboard navigation
                  onClick={() => {
                    // TODO: Handle result selection
                    appActions.closeSearch()
                  }}
                />
              ))}
            </div>
          ) : localQuery.trim() ? (
            <div className="p-8 text-center text-muted-foreground">
              <Search className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p>No results found for "{localQuery}"</p>
              <p className="text-sm mt-1">Try a different search term</p>
            </div>
          ) : (
            <div className="p-8 text-center text-muted-foreground">
              <Search className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p>Start typing to search</p>
              <p className="text-sm mt-1">Search through documents, conversations, and code</p>
            </div>
          )}
        </div>

        {/* Quick actions */}
        {!localQuery.trim() && (
          <div className="p-4 border-t border-border">
            <div className="text-xs text-muted-foreground uppercase tracking-wider mb-3">
              Quick Actions
            </div>
            <div className="grid grid-cols-2 gap-2">
              <Button
                variant="ghost"
                size="sm"
                className="justify-start h-auto p-3"
              >
                <File className="w-4 h-4 mr-3" />
                <div className="text-left">
                  <div className="font-medium">Browse Documents</div>
                  <div className="text-xs text-muted-foreground">View all uploaded files</div>
                </div>
              </Button>

              <Button
                variant="ghost"
                size="sm"
                className="justify-start h-auto p-3"
              >
                <MessageSquare className="w-4 h-4 mr-3" />
                <div className="text-left">
                  <div className="font-medium">Recent Conversations</div>
                  <div className="text-xs text-muted-foreground">View chat history</div>
                </div>
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

