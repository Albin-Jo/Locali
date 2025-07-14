// frontend/src/components/documents/DocumentList.tsx

import React, { useState } from 'react'
import { FileText, Upload, Search, Trash2, MoreVertical, File, Code } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { DocumentUpload } from './DocumentUpload'
import { useDocuments, useDeleteDocument } from '@/lib/queries'
import { formatFileSize, formatTimeAgo } from '@/lib/utils'
import { cn } from '@/lib/utils'
import type { Document } from '@/types'

export function DocumentList() {
  const { data: documents, isLoading } = useDocuments()
  const deleteDocument = useDeleteDocument()
  const [searchQuery, setSearchQuery] = useState('')
  const [showUpload, setShowUpload] = useState(false)

  const filteredDocuments = documents?.filter(doc =>
    doc.filename.toLowerCase().includes(searchQuery.toLowerCase()) ||
    doc.content_type.toLowerCase().includes(searchQuery.toLowerCase())
  ) || []

  const handleDelete = (documentId: string, filename: string) => {
    if (confirm(`Delete "${filename}"?`)) {
      deleteDocument.mutate(documentId)
    }
  }

  const getFileIcon = (contentType: string) => {
    if (contentType.startsWith('text/x-') || contentType.includes('javascript') || contentType.includes('python')) {
      return Code
    }
    return File
  }

  if (isLoading) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <div className="loading-shimmer w-32 h-4 rounded mb-2" />
          <div className="loading-shimmer w-24 h-4 rounded" />
        </div>
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-border">
        <div className="flex items-center gap-2 mb-3">
          <Button
            onClick={() => setShowUpload(true)}
            className="flex-1"
            size="sm"
          >
            <Upload className="w-4 h-4 mr-2" />
            Upload
          </Button>
        </div>

        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            placeholder="Search documents..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10 h-9"
          />
        </div>
      </div>

      {/* Document list */}
      <div className="flex-1 overflow-y-auto">
        {filteredDocuments.length === 0 ? (
          <div className="p-4 text-center text-muted-foreground">
            {documents?.length === 0 ? (
              <>
                <FileText className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p>No documents uploaded</p>
                <p className="text-xs mt-1">Upload files to get started</p>
              </>
            ) : (
              <p>No documents match your search</p>
            )}
          </div>
        ) : (
          <div className="p-2 space-y-1">
            {filteredDocuments.map(document => (
              <DocumentItem
                key={document.id}
                document={document}
                onDelete={() => handleDelete(document.id, document.filename)}
                isDeleting={deleteDocument.isPending}
              />
            ))}
          </div>
        )}
      </div>

      {/* Upload modal */}
      {showUpload && (
        <DocumentUpload
          onClose={() => setShowUpload(false)}
        />
      )}
    </div>
  )
}

