// frontend/src/pages/DocumentsPage.tsx

import React, { useState } from 'react'
import {
  Upload,
  Search,
  Filter,
  Grid,
  List,
  FileText,
  Code,
  File,
  Download,
  Trash2,
  Eye,
  MoreVertical
} from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { DocumentUpload } from '@/components/documents/DocumentUpload'
import { useDocuments, useDeleteDocument } from '@/lib/queries'
import { formatFileSize, formatTimeAgo } from '@/lib/utils'
import { cn } from '@/lib/utils'
import type { Document } from '@/types'

type ViewMode = 'grid' | 'list'
type FilterType = 'all' | 'code' | 'docs' | 'data'

export function DocumentsPage() {
  const { data: documents, isLoading } = useDocuments()
  const deleteDocument = useDeleteDocument()
  const [searchQuery, setSearchQuery] = useState('')
  const [viewMode, setViewMode] = useState<ViewMode>('grid')
  const [filter, setFilter] = useState<FilterType>('all')
  const [showUpload, setShowUpload] = useState(false)

  const filteredDocuments = documents?.filter(doc => {
    const matchesSearch = doc.filename.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         doc.content_type.toLowerCase().includes(searchQuery.toLowerCase())

    const matchesFilter = filter === 'all' ||
      (filter === 'code' && doc.content_type.includes('python') || doc.content_type.includes('javascript') || doc.content_type.includes('typescript')) ||
      (filter === 'docs' && (doc.content_type.includes('markdown') || doc.content_type.includes('text'))) ||
      (filter === 'data' && (doc.content_type.includes('json') || doc.content_type.includes('yaml')))

    return matchesSearch && matchesFilter
  }) || []

  const handleDelete = (documentId: string, filename: string) => {
    if (confirm(`Delete "${filename}"?`)) {
      deleteDocument.mutate(documentId)
    }
  }

  const getFileIcon = (contentType: string) => {
    if (contentType.includes('python') || contentType.includes('javascript') || contentType.includes('typescript')) {
      return Code
    }
    if (contentType.includes('markdown') || contentType.includes('text')) {
      return FileText
    }
    return File
  }

  const filters = [
    { id: 'all', label: 'All Files', count: documents?.length || 0 },
    {
      id: 'code',
      label: 'Code',
      count: documents?.filter(d =>
        d.content_type.includes('python') ||
        d.content_type.includes('javascript') ||
        d.content_type.includes('typescript')
      ).length || 0
    },
    {
      id: 'docs',
      label: 'Documents',
      count: documents?.filter(d =>
        d.content_type.includes('markdown') ||
        d.content_type.includes('text')
      ).length || 0
    },
    {
      id: 'data',
      label: 'Data',
      count: documents?.filter(d =>
        d.content_type.includes('json') ||
        d.content_type.includes('yaml')
      ).length || 0
    }
  ]

  if (isLoading) {
    return <LoadingScreen />
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="border-b border-border bg-card p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-2xl font-semibold text-foreground">Documents</h1>
            <p className="text-muted-foreground">
              Manage and search through your uploaded files
            </p>
          </div>

          <Button onClick={() => setShowUpload(true)}>
            <Upload className="w-4 h-4 mr-2" />
            Upload Files
          </Button>
        </div>

        {/* Search and filters */}
        <div className="flex items-center gap-4">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input
              placeholder="Search documents..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
          </div>

          <div className="flex items-center gap-2">
            {filters.map(f => (
              <Button
                key={f.id}
                variant={filter === f.id ? 'default' : 'outline'}
                size="sm"
                onClick={() => setFilter(f.id as FilterType)}
              >
                {f.label} ({f.count})
              </Button>
            ))}
          </div>

          <div className="flex items-center border border-border rounded-lg">
            <Button
              variant={viewMode === 'grid' ? 'default' : 'ghost'}
              size="sm"
              onClick={() => setViewMode('grid')}
              className="rounded-r-none"
            >
              <Grid className="w-4 h-4" />
            </Button>
            <Button
              variant={viewMode === 'list' ? 'default' : 'ghost'}
              size="sm"
              onClick={() => setViewMode('list')}
              className="rounded-l-none"
            >
              <List className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {filteredDocuments.length === 0 ? (
          <div className="text-center py-12">
            {documents?.length === 0 ? (
              <>
                <FileText className="w-16 h-16 mx-auto mb-4 text-muted-foreground opacity-50" />
                <h3 className="text-lg font-semibold text-foreground mb-2">No documents uploaded</h3>
                <p className="text-muted-foreground mb-4">
                  Upload code files, documentation, or data files to get started
                </p>
                <Button onClick={() => setShowUpload(true)}>
                  <Upload className="w-4 h-4 mr-2" />
                  Upload Your First Document
                </Button>
              </>
            ) : (
              <>
                <Search className="w-16 h-16 mx-auto mb-4 text-muted-foreground opacity-50" />
                <h3 className="text-lg font-semibold text-foreground mb-2">No results found</h3>
                <p className="text-muted-foreground">
                  Try adjusting your search or filter criteria
                </p>
              </>
            )}
          </div>
        ) : (
          <div className={cn(
            viewMode === 'grid'
              ? 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4'
              : 'space-y-2'
          )}>
            {filteredDocuments.map(document => (
              viewMode === 'grid' ? (
                <DocumentCard
                  key={document.id}
                  document={document}
                  onDelete={() => handleDelete(document.id, document.filename)}
                  isDeleting={deleteDocument.isPending}
                />
              ) : (
                <DocumentRow
                  key={document.id}
                  document={document}
                  onDelete={() => handleDelete(document.id, document.filename)}
                  isDeleting={deleteDocument.isPending}
                />
              )
            ))}
          </div>
        )}
      </div>

      {/* Upload modal */}
      {showUpload && (
        <DocumentUpload onClose={() => setShowUpload(false)} />
      )}
    </div>
  )
}

// Document Card Component
function DocumentCard({
  document,
  onDelete,
  isDeleting
}: {
  document: Document
  onDelete: () => void
  isDeleting: boolean
}) {
  const [showActions, setShowActions] = useState(false)

  const getFileIcon = (contentType: string) => {
    if (contentType.includes('python') || contentType.includes('javascript') || contentType.includes('typescript')) {
      return Code
    }
    if (contentType.includes('markdown') || contentType.includes('text')) {
      return FileText
    }
    return File
  }

  const Icon = getFileIcon(document.content_type)

  return (
    <div
      className="group p-4 border border-border rounded-lg hover:shadow-md transition-all cursor-pointer"
      onMouseEnter={() => setShowActions(true)}
      onMouseLeave={() => setShowActions(false)}
    >
      <div className="flex items-start justify-between mb-3">
        <Icon className="w-8 h-8 text-primary" />

        {showActions && (
          <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
            <Button variant="ghost" size="sm" className="h-6 w-6 p-0">
              <Eye className="w-3 h-3" />
            </Button>
            <Button variant="ghost" size="sm" className="h-6 w-6 p-0">
              <Download className="w-3 h-3" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={onDelete}
              disabled={isDeleting}
              className="h-6 w-6 p-0 text-destructive hover:text-destructive"
            >
              <Trash2 className="w-3 h-3" />
            </Button>
          </div>
        )}
      </div>

      <h3 className="font-medium text-foreground mb-2 truncate" title={document.filename}>
        {document.filename}
      </h3>

      <div className="space-y-1 text-xs text-muted-foreground">
        <div className="flex items-center justify-between">
          <span>{formatFileSize(document.size_bytes)}</span>
          <span>{document.total_chunks} chunks</span>
        </div>
        <div>{formatTimeAgo(document.processed_at)}</div>
        <div className="truncate">{document.content_type}</div>
      </div>
    </div>
  )
}

// Document Row Component
function DocumentRow({
  document,
  onDelete,
  isDeleting
}: {
  document: Document
  onDelete: () => void
  isDeleting: boolean
}) {
  const [showActions, setShowActions] = useState(false)

  const getFileIcon = (contentType: string) => {
    if (contentType.includes('python') || contentType.includes('javascript') || contentType.includes('typescript')) {
      return Code
    }
    if (contentType.includes('markdown') || contentType.includes('text')) {
      return FileText
    }
    return File
  }

  const Icon = getFileIcon(document.content_type)

  return (
    <div
      className="group flex items-center gap-4 p-4 border border-border rounded-lg hover:bg-accent/50 transition-colors cursor-pointer"
      onMouseEnter={() => setShowActions(true)}
      onMouseLeave={() => setShowActions(false)}
    >
      <Icon className="w-6 h-6 text-primary shrink-0" />

      <div className="flex-1 min-w-0">
        <h3 className="font-medium text-foreground truncate">
          {document.filename}
        </h3>
        <div className="flex items-center gap-3 mt-1 text-sm text-muted-foreground">
          <span>{formatFileSize(document.size_bytes)}</span>
          <span>•</span>
          <span>{document.total_chunks} chunks</span>
          <span>•</span>
          <span>{formatTimeAgo(document.processed_at)}</span>
        </div>
      </div>

      <div className="text-sm text-muted-foreground">
        {document.content_type}
      </div>

      {showActions && (
        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
            <Eye className="w-4 h-4" />
          </Button>
          <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
            <Download className="w-4 h-4" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={onDelete}
            disabled={isDeleting}
            className="h-8 w-8 p-0 text-destructive hover:text-destructive"
          >
            <Trash2 className="w-4 h-4" />
          </Button>
        </div>
      )}
    </div>
  )
}

