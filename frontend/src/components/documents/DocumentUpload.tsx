// frontend/src/components/documents/DocumentUpload.tsx

import React, { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, X, File, AlertCircle, Check } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { useUploadDocument } from '@/lib/queries'
import { formatFileSize } from '@/lib/utils'
import { cn } from '@/lib/utils'
import { SUPPORTED_FILE_TYPES, FILE_SIZE_LIMITS } from '@/types'
import toast from 'react-hot-toast'

interface DocumentUploadProps {
  onClose: () => void
}

export function DocumentUpload({ onClose }: DocumentUploadProps) {
  const [uploadQueue, setUploadQueue] = useState<File[]>([])
  const [uploadedFiles, setUploadedFiles] = useState<Set<string>>(new Set())
  const uploadDocument = useUploadDocument()

  const onDrop = useCallback((acceptedFiles: File[], rejectedFiles: any[]) => {
    // Handle rejected files
    rejectedFiles.forEach(({ file, errors }) => {
      errors.forEach((error: any) => {
        if (error.code === 'file-too-large') {
          toast.error(`${file.name} is too large (max ${FILE_SIZE_LIMITS.MAX_FILE_SIZE / 1024 / 1024}MB)`)
        } else if (error.code === 'file-invalid-type') {
          toast.error(`${file.name} is not a supported file type`)
        }
      })
    })

    // Add accepted files to queue
    setUploadQueue(prev => [...prev, ...acceptedFiles])
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'text/plain': ['.txt'],
      'text/markdown': ['.md'],
      'text/x-python': ['.py'],
      'text/javascript': ['.js'],
      'text/typescript': ['.ts'],
      'text/jsx': ['.jsx'],
      'text/tsx': ['.tsx'],
      'application/json': ['.json'],
      'text/yaml': ['.yaml', '.yml'],
    },
    maxSize: FILE_SIZE_LIMITS.MAX_FILE_SIZE,
    maxFiles: FILE_SIZE_LIMITS.MAX_FILES,
  })

  const handleUpload = async (file: File) => {
    try {
      await uploadDocument.mutateAsync(file)
      setUploadedFiles(prev => new Set([...prev, file.name]))
      toast.success(`${file.name} uploaded successfully`)
    } catch (error) {
      toast.error(`Failed to upload ${file.name}`)
    }
  }

  const handleUploadAll = async () => {
    for (const file of uploadQueue) {
      if (!uploadedFiles.has(file.name)) {
        await handleUpload(file)
      }
    }
  }

  const removeFromQueue = (fileName: string) => {
    setUploadQueue(prev => prev.filter(f => f.name !== fileName))
    setUploadedFiles(prev => {
      const newSet = new Set(prev)
      newSet.delete(fileName)
      return newSet
    })
  }

  const pendingUploads = uploadQueue.filter(f => !uploadedFiles.has(f.name))

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-card border border-border rounded-lg w-full max-w-2xl max-h-[80vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-border">
          <h2 className="text-lg font-semibold">Upload Documents</h2>
          <Button variant="ghost" size="sm" onClick={onClose}>
            <X className="w-4 h-4" />
          </Button>
        </div>

        {/* Drop zone */}
        <div className="p-6">
          <div
            {...getRootProps()}
            className={cn(
              'border-2 border-dashed rounded-lg p-8 text-center transition-colors',
              isDragActive
                ? 'border-primary bg-primary/10'
                : 'border-muted-foreground/25 hover:border-muted-foreground/50'
            )}
          >
            <input {...getInputProps()} />

            <Upload className="w-8 h-8 mx-auto mb-4 text-muted-foreground" />

            {isDragActive ? (
              <p className="text-primary font-medium">Drop files here</p>
            ) : (
              <>
                <p className="font-medium mb-2">Drag & drop files here, or click to select</p>
                <p className="text-sm text-muted-foreground">
                  Supports: {SUPPORTED_FILE_TYPES.ALL.join(', ')}
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  Max {FILE_SIZE_LIMITS.MAX_FILE_SIZE / 1024 / 1024}MB per file, {FILE_SIZE_LIMITS.MAX_FILES} files total
                </p>
              </>
            )}
          </div>
        </div>

        {/* File queue */}
        {uploadQueue.length > 0 && (
          <div className="flex-1 border-t border-border overflow-hidden">
            <div className="p-4 border-b border-border">
              <div className="flex items-center justify-between">
                <h3 className="font-medium">Files to Upload ({uploadQueue.length})</h3>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setUploadQueue([])}
                  >
                    Clear All
                  </Button>
                  <Button
                    size="sm"
                    onClick={handleUploadAll}
                    disabled={uploadDocument.isPending || pendingUploads.length === 0}
                  >
                    Upload All ({pendingUploads.length})
                  </Button>
                </div>
              </div>
            </div>

            <div className="max-h-60 overflow-y-auto p-4 space-y-2">
              {uploadQueue.map((file) => {
                const isUploaded = uploadedFiles.has(file.name)
                const isUploading = uploadDocument.isPending

                return (
                  <div
                    key={file.name}
                    className="flex items-center gap-3 p-3 bg-muted/50 rounded-lg"
                  >
                    <File className="w-4 h-4 text-muted-foreground shrink-0" />

                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">{file.name}</p>
                      <p className="text-xs text-muted-foreground">
                        {formatFileSize(file.size)}
                      </p>
                    </div>

                    <div className="flex items-center gap-2">
                      {isUploaded ? (
                        <Check className="w-4 h-4 text-green-500" />
                      ) : isUploading ? (
                        <div className="w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                      ) : (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleUpload(file)}
                          className="h-6 px-2 text-xs"
                        >
                          Upload
                        </Button>
                      )}

                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => removeFromQueue(file.name)}
                        className="h-6 w-6 p-0"
                      >
                        <X className="w-3 h-3" />
                      </Button>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {/* Footer */}
        <div className="p-6 border-t border-border">
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={onClose}>
              {uploadedFiles.size > 0 ? 'Done' : 'Cancel'}
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}

