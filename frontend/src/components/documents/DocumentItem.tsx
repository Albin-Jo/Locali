// frontend/src/components/documents/DocumentItem.tsx

import React, { useState } from 'react'
import { FileText, Trash2, MoreVertical, Eye, Download } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { formatFileSize, formatTimeAgo } from '@/lib/utils'
import { cn } from '@/lib/utils'
import type { Document } from '@/types'

interface DocumentItemProps {
  document: Document
  onDelete: () => void
  isDeleting: boolean
}

export function DocumentItem({ document, onDelete, isDeleting }: DocumentItemProps) {
  const [showActions, setShowActions] = useState(false)

  const getFileTypeColor = (contentType: string) => {
    if (contentType.includes('python')) return 'text-blue-500'
    if (contentType.includes('javascript')) return 'text-yellow-500'
    if (contentType.includes('typescript')) return 'text-blue-600'
    if (contentType.includes('markdown')) return 'text-green-500'
    if (contentType.includes('json')) return 'text-orange-500'
    return 'text-muted-foreground'
  }

  return (
    <div
      className={cn(
        'group p-3 rounded-lg transition-colors',
        'hover:bg-accent/50 cursor-pointer'
      )}
      onMouseEnter={() => setShowActions(true)}
      onMouseLeave={() => setShowActions(false)}
    >
      <div className="flex items-start gap-3">
        <FileText className={cn('w-4 h-4 mt-0.5 shrink-0', getFileTypeColor(document.content_type))} />

        <div className="flex-1 min-w-0">
          <h4 className="text-sm font-medium truncate text-foreground">
            {document.filename}
          </h4>

          <div className="flex items-center gap-2 mt-1 text-xs text-muted-foreground">
            <span>{formatFileSize(document.size_bytes)}</span>
            <span>•</span>
            <span>{document.total_chunks} chunks</span>
            <span>•</span>
            <span>{formatTimeAgo(document.processed_at)}</span>
          </div>

          <div className="text-xs text-muted-foreground mt-1">
            {document.content_type}
          </div>
        </div>

        {/* Actions */}
        {showActions && (
          <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
            <Button
              variant="ghost"
              size="sm"
              className="h-6 w-6 p-0"
            >
              <Eye className="w-3 h-3" />
            </Button>

            <Button
              variant="ghost"
              size="sm"
              onClick={onDelete}
              className="h-6 w-6 p-0 text-destructive hover:text-destructive"
              disabled={isDeleting}
            >
              <Trash2 className="w-3 h-3" />
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}

