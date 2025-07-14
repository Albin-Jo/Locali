// frontend/src/components/editor/MonacoCodeViewer.tsx

import React, { useRef, useEffect } from 'react'
import Editor from '@monaco-editor/react'
import { useAppStore } from '@/store'
import { cn } from '@/lib/utils'

interface MonacoCodeViewerProps {
  code: string
  language: string
  readOnly?: boolean
  height?: string | number
  className?: string
  onCodeChange?: (code: string) => void
  showMinimap?: boolean
  wordWrap?: boolean
}

export function MonacoCodeViewer({
  code,
  language,
  readOnly = true,
  height = 400,
  className,
  onCodeChange,
  showMinimap = false,
  wordWrap = true,
}: MonacoCodeViewerProps) {
  const { theme } = useAppStore()
  const editorRef = useRef<any>(null)

  const handleEditorDidMount = (editor: any, monaco: any) => {
    editorRef.current = editor

    // Configure Monaco themes
    monaco.editor.defineTheme('locali-dark', {
      base: 'vs-dark',
      inherit: true,
      rules: [
        { token: 'comment', foreground: '#6A9955' },
        { token: 'keyword', foreground: '#569CD6' },
        { token: 'string', foreground: '#CE9178' },
        { token: 'number', foreground: '#B5CEA8' },
        { token: 'function', foreground: '#DCDCAA' },
        { token: 'type', foreground: '#4EC9B0' },
      ],
      colors: {
        'editor.background': '#0f0f23',
        'editor.foreground': '#ffffff',
        'editor.lineHighlightBackground': '#16162a',
        'editor.selectionBackground': '#264f78',
        'editor.selectionHighlightBackground': '#add6ff26',
        'editorLineNumber.foreground': '#858585',
        'editorLineNumber.activeForeground': '#c6c6c6',
        'editor.findMatchBackground': '#515c6a',
        'editor.findMatchHighlightBackground': '#ea5c0055',
      }
    })

    monaco.editor.defineTheme('locali-light', {
      base: 'vs',
      inherit: true,
      rules: [
        { token: 'comment', foreground: '#008000' },
        { token: 'keyword', foreground: '#0000ff' },
        { token: 'string', foreground: '#a31515' },
        { token: 'number', foreground: '#098658' },
        { token: 'function', foreground: '#795e26' },
        { token: 'type', foreground: '#267f99' },
      ],
      colors: {
        'editor.background': '#ffffff',
        'editor.foreground': '#000000',
        'editor.lineHighlightBackground': '#f0f0f0',
        'editor.selectionBackground': '#add6ff',
        'editorLineNumber.foreground': '#237893',
      }
    })

    // Set theme
    monaco.editor.setTheme(theme === 'dark' ? 'locali-dark' : 'locali-light')
  }

  // Update theme when it changes
  useEffect(() => {
    if (editorRef.current) {
      const monaco = (window as any).monaco
      if (monaco) {
        monaco.editor.setTheme(theme === 'dark' ? 'locali-dark' : 'locali-light')
      }
    }
  }, [theme])

  return (
    <div className={cn('border border-border rounded-lg overflow-hidden', className)}>
      <Editor
        height={height}
        language={language}
        value={code}
        onChange={onCodeChange}
        onMount={handleEditorDidMount}
        options={{
          readOnly,
          minimap: { enabled: showMinimap },
          wordWrap: wordWrap ? 'on' : 'off',
          scrollBeyondLastLine: false,
          automaticLayout: true,
          tabSize: 2,
          insertSpaces: true,
          detectIndentation: true,
          renderLineHighlight: 'line',
          selectionHighlight: false,
          occurrencesHighlight: false,
          fontSize: 14,
          fontFamily: 'JetBrains Mono, Monaco, Consolas, monospace',
          lineNumbers: 'on',
          glyphMargin: false,
          folding: true,
          lineDecorationsWidth: 10,
          lineNumbersMinChars: 3,
          renderWhitespace: 'selection',
          smoothScrolling: true,
          cursorBlinking: 'smooth',
          cursorSmoothCaretAnimation: true,
          contextmenu: false,
          links: false,
          colorDecorators: true,
          dragAndDrop: false,
          copyWithSyntaxHighlighting: true,
        }}
      />
    </div>
  )
}



