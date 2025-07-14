// frontend/src/pages/ChatPage.tsx

import React, { useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { MessageList } from '@/components/chat/MessageList'
import { ChatInput } from '@/components/chat/ChatInput'
import { useConversation } from '@/lib/queries'
import { useAppStore, appActions, chatActions } from '@/store'
import { LoadingScreen } from '@/components/ui/LoadingScreen'

export function ChatPage() {
  const { conversationId } = useParams<{ conversationId: string }>()
  const { currentConversationId } = useAppStore()
  const { data: conversation, isLoading } = useConversation(conversationId)

  // Update current conversation when URL changes
  useEffect(() => {
    if (conversationId && conversationId !== currentConversationId) {
      appActions.setCurrentConversation(conversationId)
    }
  }, [conversationId, currentConversationId])

  // Load messages when conversation data is available
  useEffect(() => {
    if (conversation?.messages) {
      chatActions.setMessages(conversation.messages)
    }
  }, [conversation])

  // Show loading state for initial load
  if (isLoading && conversationId) {
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
      {/* Chat messages */}
      <div className="flex-1 overflow-hidden">
        <MessageList />
      </div>

      {/* Chat input */}
      <ChatInput />
    </div>
  )
}

