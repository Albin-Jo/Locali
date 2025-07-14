// frontend/src/components/chat/TypingIndicator.tsx

import React from 'react'

export function TypingIndicator() {
  return (
    <div className="flex gap-4 p-4">
      <div className="w-8 h-8 rounded-full bg-muted flex items-center justify-center text-sm font-medium">
        AI
      </div>

      <div className="flex items-center">
        <div className="typing-dots">
          <div className="typing-dot" style={{ '--delay': 0 } as any} />
          <div className="typing-dot" style={{ '--delay': 1 } as any} />
          <div className="typing-dot" style={{ '--delay': 2 } as any} />
        </div>
        <span className="ml-3 text-sm text-muted-foreground">
          Assistant is typing...
        </span>
      </div>
    </div>
  )
}

