// frontend/src/components/chat/ChatInput.tsx

import React, { useState, useRef, useCallback } from 'react'
import { Send, Paperclip, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { useChatStore, chatActions, useAppStore } from '@/store'
import { useSendMessage } from '@/lib/queries'
import { useDropzone } from 'react-dropzone'
import { cn } from '@/lib/utils'
import toast from 'react-hot-toast'

export function ChatInput() {
  const { inputValue, isStreaming, isLoading } = useChatStore()
  const { currentConversationId, currentModelName } = useAppStore()
  const [isExpanded, setIsExpanded] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const sendMessage = useSendMessage()

  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    chatActions.setInputValue(e.target.value)

    // Auto-resize textarea
    const textarea = e.target
    textarea.style.height = 'auto'
    textarea.style.height = Math.min(textarea.scrollHeight, 200) + 'px'

    setIsExpanded(textarea.scrollHeight > 60)
  }

  const handleSubmit = useCallback(async () => {
    if (!inputValue.trim() || isStreaming || !currentConversationId) return

    const message = inputValue.trim()
    chatActions.setInputValue('')

    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      setIsExpanded(false)
    }

    try {
      await sendMessage.mutateAsync({
        conversationId: currentConversationId,
        data: {
          message,
          model_name: currentModelName,
          temperature: 0.3,
          max_tokens: 2048,
        },
      })
    } catch (error) {
      toast.error('Failed to send message')
      chatActions.setInputValue(message) // Restore message on error
    }
  }, [inputValue, isStreaming, currentConversationId, currentModelName, sendMessage])

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  const onDrop = useCallback((acceptedFiles: File[]) => {
    // Handle file uploads - integrate with document upload
    console.log('Files dropped:', acceptedFiles)
    toast.success(`${acceptedFiles.length} file(s) ready to upload`)
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    noClick: true,
    multiple: true,
    accept: {
      'text/*': ['.txt', '.md', '.py', '.js', '.ts', '.jsx', '.tsx'],
      'application/json': ['.json'],
      'text/yaml': ['.yaml', '.yml'],
    },
  })

  const isDisabled = isStreaming || isLoading || !currentConversationId

  return (
    <div className="border-t border-border bg-card">
      <div
        {...getRootProps()}
        className={cn(
          'p-4 transition-colors',
          isDragActive && 'bg-primary/10 border-primary/50'
        )}
      >
        <input {...getInputProps()} />

        {isDragActive && (
          <div className="absolute inset-0 bg-primary/10 border-2 border-dashed border-primary rounded-lg flex items-center justify-center z-10">
            <div className="text-center">
              <Paperclip className="w-8 h-8 text-primary mx-auto mb-2" />
              <p className="text-sm font-medium text-primary">
                Drop files to upload
              </p>
            </div>
          </div>
        )}

        <div className="flex items-end gap-3">
          {/* Attachment button */}
          <Button
            variant="ghost"
            size="icon"
            className="shrink-0"
            disabled={isDisabled}
          >
            <Paperclip className="w-4 h-4" />
          </Button>

          {/* Text input */}
          <div className="flex-1 relative">
            <textarea
              ref={textareaRef}
              value={inputValue}
              onChange={handleInputChange}
              onKeyDown={handleKeyDown}
              placeholder={
                currentConversationId
                  ? "Ask about code, get explanations, or request improvements..."
                  : "Start a new conversation to begin..."
              }
              disabled={isDisabled}
              className={cn(
                'w-full resize-none rounded-lg border border-border bg-background px-4 py-3 text-sm',
                'focus:outline-none focus:ring-2 focus:ring-ring focus:border-ring',
                'placeholder:text-muted-foreground',
                'disabled:opacity-50 disabled:cursor-not-allowed',
                isExpanded ? 'min-h-[120px]' : 'min-h-[48px]'
              )}
              rows={1}
            />

            {/* Character count for long messages */}
            {inputValue.length > 1000 && (
              <div className="absolute bottom-2 right-2 text-xs text-muted-foreground">
                {inputValue.length}/4000
              </div>
            )}
          </div>

          {/* Send button */}
          <Button
            onClick={handleSubmit}
            disabled={isDisabled || !inputValue.trim()}
            className="shrink-0"
          >
            {isStreaming || isLoading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
          </Button>
        </div>

        {/* Input hints */}
        <div className="flex items-center justify-between mt-2 text-xs text-muted-foreground">
          <div className="flex items-center gap-4">
            <span>⌘+Enter to send</span>
            <span>Shift+Enter for new line</span>
            <span>Drag files to upload</span>
          </div>

          {currentModelName && (
            <span className="flex items-center gap-1">
              Using {currentModelName}
            </span>
          )}
        </div>
      </div>
    </div>
  )
}

