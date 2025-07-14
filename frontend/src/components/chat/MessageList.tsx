// frontend/src/components/chat/MessageList.tsx

import React, { useEffect, useRef } from 'react'
import { Message as MessageComponent } from './Message'
import { TypingIndicator } from './TypingIndicator'
import { useChatStore } from '@/store'
import { cn } from '@/lib/utils'

export function MessageList() {
  const { messages, isStreaming } = useChatStore()
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, isStreaming])

  return (
    <div className="flex-1 overflow-y-auto px-4 py-6">
      <div className="max-w-4xl mx-auto space-y-6">
        {messages.length === 0 ? (
          <div className="text-center py-12">
            <h3 className="text-lg font-semibold text-foreground mb-2">
              Welcome to Locali
            </h3>
            <p className="text-muted-foreground">
              Start a conversation with your AI coding assistant
            </p>
          </div>
        ) : (
          messages.map((message, index) => (
            <MessageComponent
              key={message.id}
              message={message}
              isLast={index === messages.length - 1}
              isStreaming={isStreaming && index === messages.length - 1 && message.role === 'assistant'}
            />
          ))
        )}

        {isStreaming && <TypingIndicator />}

        <div ref={messagesEndRef} />
      </div>
    </div>
  )
}

