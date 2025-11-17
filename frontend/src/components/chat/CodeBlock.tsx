// frontend/src/components/chat/CodeBlock.tsx

import React, { useState, useEffect, useRef } from 'react'
import { Copy, Check, Play, FileText } from 'lucide-react'
import hljs from 'highlight.js'
import { Button } from '@/components/ui/Button'
import { useClipboard } from '@/hooks/useClipboard'
import { cn } from '@/lib/utils'

interface CodeBlockProps {
  code: string
  language: string
  className?: string
}

export function CodeBlock({ code, language, className }: CodeBlockProps) {
  const { copyToClipboard, hasCopied } = useClipboard()
  const [isExpanded, setIsExpanded] = useState(false)
  const codeRef = useRef<HTMLElement>(null)

  const shouldTruncate = code.split('\n').length > 10
  const displayCode = isExpanded || !shouldTruncate
    ? code
    : code.split('\n').slice(0, 10).join('\n')

  // Apply syntax highlighting when code changes
  useEffect(() => {
    if (codeRef.current) {
      // Normalize language name for highlight.js
      const normalizedLang = normalizeLanguage(language)

      // Set the code content
      codeRef.current.textContent = displayCode

      // Apply highlighting if language is supported
      if (normalizedLang && hljs.getLanguage(normalizedLang)) {
        codeRef.current.className = `hljs language-${normalizedLang}`
        hljs.highlightElement(codeRef.current)
      } else {
        // Auto-detect if no language specified or language not found
        codeRef.current.className = 'hljs'
        hljs.highlightElement(codeRef.current)
      }
    }
  }, [displayCode, language])

  const handleCopy = () => {
    copyToClipboard(code)
  }

  // Normalize language aliases to highlight.js language names
  const normalizeLanguage = (lang: string): string => {
    const languageMap: Record<string, string> = {
      'js': 'javascript',
      'ts': 'typescript',
      'py': 'python',
      'rb': 'ruby',
      'sh': 'bash',
      'yml': 'yaml',
      'md': 'markdown',
      'json': 'json',
      'jsx': 'javascript',
      'tsx': 'typescript',
    }

    const normalized = lang?.toLowerCase() || ''
    return languageMap[normalized] || normalized
  }

  return (
    <div className={cn('relative group', className)}>
      {/* Header */}
      <div className="flex items-center justify-between bg-muted px-4 py-2 rounded-t-lg border border-border">
        <div className="flex items-center gap-2">
          <FileText className="w-4 h-4 text-muted-foreground" />
          <span className="text-sm font-medium text-foreground">
            {language || 'plaintext'}
          </span>
        </div>

        <div className="flex items-center gap-1">
          {language === 'python' && (
            <Button
              variant="ghost"
              size="sm"
              className="h-7 px-2 text-xs opacity-0 group-hover:opacity-100 transition-opacity"
            >
              <Play className="w-3 h-3 mr-1" />
              Run
            </Button>
          )}

          <Button
            variant="ghost"
            size="sm"
            onClick={handleCopy}
            className="h-7 px-2 text-xs opacity-0 group-hover:opacity-100 transition-opacity"
          >
            {hasCopied ? (
              <Check className="w-3 h-3" />
            ) : (
              <Copy className="w-3 h-3" />
            )}
          </Button>
        </div>
      </div>

      {/* Code content */}
      <div className="bg-card border-x border-b border-border rounded-b-lg overflow-hidden">
        <pre className="p-4 overflow-x-auto text-sm">
          <code ref={codeRef} className={`language-${language}`} />
        </pre>

        {shouldTruncate && !isExpanded && (
          <div className="border-t border-border bg-muted/50 px-4 py-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsExpanded(true)}
              className="h-7 text-xs text-muted-foreground hover:text-foreground"
            >
              Show more ({code.split('\n').length - 10} more lines)
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}

