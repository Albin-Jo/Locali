// frontend/src/components/chat/Message.tsx

import React, { useState, useMemo } from 'react'
import { Copy, Insert, MoreHorizontal, Check } from 'lucide-react'
import MarkdownIt from 'markdown-it'
import { Button } from '@/components/ui/Button'
import { CodeBlock } from './CodeBlock'
import { useClipboard } from '@/hooks/useClipboard'
import { extractCodeBlocks, formatTimeAgo } from '@/lib/utils'
import { cn } from '@/lib/utils'
import type { Message as MessageType } from '@/types'

// Initialize markdown-it with sensible defaults
const md = new MarkdownIt({
  html: false, // Disable HTML tags in source for security
  breaks: true, // Convert '\n' in paragraphs into <br>
  linkify: true, // Auto-convert URL-like text to links
  typographer: true, // Enable smartquotes and other replacements
})

interface MessageProps {
  message: MessageType
  isLast?: boolean
  isStreaming?: boolean
}

export function Message({ message, isLast, isStreaming }: MessageProps) {
  const [showActions, setShowActions] = useState(false)
  const { copyToClipboard, hasCopied } = useClipboard()

  // Extract code blocks
  const codeBlocks = extractCodeBlocks(message.content)

  // Remove code blocks from text content
  const textContent = message.content.replace(/```(\w+)?\n([\s\S]*?)```/g, '')

  // Render markdown to HTML (memoized for performance)
  const renderedHtml = useMemo(() => {
    if (!textContent.trim()) return ''
    return md.render(textContent.trim())
  }, [textContent])

  const handleCopy = () => {
    copyToClipboard(message.content)
  }

  const isUser = message.role === 'user'
  const isAssistant = message.role === 'assistant'

  return (
    <div
      className={cn(
        'group flex gap-4 p-4 rounded-lg transition-colors',
        isUser && 'message-user ml-12',
        isAssistant && 'message-assistant',
        isStreaming && 'animate-pulse'
      )}
      onMouseEnter={() => setShowActions(true)}
      onMouseLeave={() => setShowActions(false)}
    >
      {/* Avatar */}
      <div
        className={cn(
          'w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium shrink-0',
          isUser ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground'
        )}
      >
        {isUser ? 'You' : 'AI'}
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-sm font-medium">
            {isUser ? 'You' : 'Assistant'}
          </span>
          <span className="text-xs text-muted-foreground">
            {formatTimeAgo(message.timestamp)}
          </span>
        </div>

        {/* Text content with markdown rendering */}
        {renderedHtml && (
          <div
            className="prose prose-sm max-w-none text-foreground mb-4 markdown-content"
            dangerouslySetInnerHTML={{ __html: renderedHtml }}
          />
        )}

        {/* Code blocks */}
        {codeBlocks.map((block, index) => (
          <CodeBlock
            key={index}
            code={block.code}
            language={block.language}
            className="mb-4 last:mb-0"
          />
        ))}

        {/* Message actions */}
        {showActions && !isStreaming && (
          <div className="flex items-center gap-1 mt-3 opacity-0 group-hover:opacity-100 transition-opacity">
            <Button
              variant="ghost"
              size="sm"
              onClick={handleCopy}
              className="h-7 px-2 text-xs"
            >
              {hasCopied ? (
                <Check className="w-3 h-3 mr-1" />
              ) : (
                <Copy className="w-3 h-3 mr-1" />
              )}
              {hasCopied ? 'Copied' : 'Copy'}
            </Button>

            {isAssistant && codeBlocks.length > 0 && (
              <>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 px-2 text-xs"
                >
                  <Insert className="w-3 h-3 mr-1" />
                  Insert
                </Button>

                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 px-2 text-xs"
                >
                  <MoreHorizontal className="w-3 h-3 mr-1" />
                  Explain
                </Button>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

