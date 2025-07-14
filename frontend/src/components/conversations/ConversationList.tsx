// frontend/src/components/conversations/ConversationList.tsx

import React from 'react'
import { Plus, Search, MoreVertical } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { ConversationItem } from './ConversationItem'
import { useConversations, useCreateConversation } from '@/lib/queries'
import { useAppStore, appActions } from '@/store'
import { cn } from '@/lib/utils'

export function ConversationList() {
  const { data: conversations, isLoading } = useConversations()
  const { currentConversationId } = useAppStore()
  const createConversation = useCreateConversation()
  const [searchQuery, setSearchQuery] = React.useState('')

  const handleNewConversation = () => {
    createConversation.mutate({})
  }

  const filteredConversations = conversations?.filter(conv =>
    conv.title?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    searchQuery === ''
  ) || []

  const groupedConversations = React.useMemo(() => {
    const now = new Date()
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
    const yesterday = new Date(today.getTime() - 24 * 60 * 60 * 1000)
    const lastWeek = new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000)

    const groups = {
      today: [] as typeof filteredConversations,
      yesterday: [] as typeof filteredConversations,
      lastWeek: [] as typeof filteredConversations,
      older: [] as typeof filteredConversations,
    }

    filteredConversations.forEach(conv => {
      const updatedAt = new Date(conv.updated_at)

      if (updatedAt >= today) {
        groups.today.push(conv)
      } else if (updatedAt >= yesterday) {
        groups.yesterday.push(conv)
      } else if (updatedAt >= lastWeek) {
        groups.lastWeek.push(conv)
      } else {
        groups.older.push(conv)
      }
    })

    return groups
  }, [filteredConversations])

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
            onClick={handleNewConversation}
            disabled={createConversation.isPending}
            className="flex-1"
            size="sm"
          >
            <Plus className="w-4 h-4 mr-2" />
            New Chat
          </Button>
        </div>

        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            placeholder="Search conversations..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10 h-9"
          />
        </div>
      </div>

      {/* Conversation list */}
      <div className="flex-1 overflow-y-auto">
        {filteredConversations.length === 0 ? (
          <div className="p-4 text-center text-muted-foreground">
            <p>No conversations yet</p>
            <p className="text-xs mt-1">Start your first chat above</p>
          </div>
        ) : (
          <div className="p-2">
            {Object.entries(groupedConversations).map(([period, convs]) => {
              if (convs.length === 0) return null

              const labels = {
                today: 'Today',
                yesterday: 'Yesterday',
                lastWeek: 'Last 7 days',
                older: 'Older'
              }

              return (
                <div key={period} className="mb-4">
                  <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wider px-2 mb-2">
                    {labels[period as keyof typeof labels]}
                  </h3>

                  <div className="space-y-1">
                    {convs.map(conversation => (
                      <ConversationItem
                        key={conversation.id}
                        conversation={conversation}
                        isActive={conversation.id === currentConversationId}
                        onClick={() => appActions.setCurrentConversation(conversation.id)}
                      />
                    ))}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}

