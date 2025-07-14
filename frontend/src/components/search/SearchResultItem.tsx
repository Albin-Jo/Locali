// frontend/src/components/search/SearchResultItem.tsx

import React from 'react'
import { File, MessageSquare, ArrowRight, Hash } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { SearchResult } from '@/types'

interface SearchResultItemProps {
  result: SearchResult
  isSelected: boolean
  onClick: () => void
}

export function SearchResultItem({ result, isSelected, onClick }: SearchResultItemProps) {
  const getIcon = () => {
    switch (result.chunk_type) {
      case 'code':
        return Hash
      case 'markdown':
        return File
      default:
        return File
    }
  }

  const Icon = getIcon()

  return (
    <button
      onClick={onClick}
      className={cn(
        'w-full text-left p-3 rounded-lg transition-colors group',
        'hover:bg-accent hover:text-accent-foreground',
        isSelected && 'bg-accent text-accent-foreground'
      )}
    >
      <div className="flex items-start gap-3">
        <Icon className="w-4 h-4 mt-1 text-muted-foreground shrink-0" />

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-sm font-medium truncate">
              Document result
            </span>
            <span className="text-xs text-muted-foreground">
              Score: {(result.score * 100).toFixed(0)}%
            </span>
          </div>

          <p className="text-sm text-muted-foreground line-clamp-2">
            {result.content.substring(0, 150)}...
          </p>

          <div className="flex items-center gap-2 mt-2 text-xs text-muted-foreground">
            <span>{result.chunk_type}</span>
            {result.language && (
              <>
                <span>•</span>
                <span>{result.language}</span>
              </>
            )}
          </div>
        </div>

        <ArrowRight className="w-4 h-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
      </div>
    </button>
  )
}

