// frontend/src/components/conversations/ConversationItem.tsx

import React, { useState } from 'react'
import { MoreVertical, Trash2, Edit, MessageSquare } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { useDeleteConversation, useUpdateConversation } from '@/lib/queries'
import { formatTimeAgo, truncateText } from '@/lib/utils'
import { cn } from '@/lib/utils'
import type { Conversation } from '@/types'

interface ConversationItemProps {
  conversation: Conversation
  isActive: boolean
  onClick: () => void
}

export function ConversationItem({ conversation, isActive, onClick }: ConversationItemProps) {
  const [isEditing, setIsEditing] = useState(false)
  const [newTitle, setNewTitle] = useState(conversation.title || '')
  const [showActions, setShowActions] = useState(false)

  const deleteConversation = useDeleteConversation()
  const updateConversation = useUpdateConversation()

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation()
    if (confirm('Delete this conversation?')) {
      deleteConversation.mutate(conversation.id)
    }
  }

  const handleEdit = (e: React.MouseEvent) => {
    e.stopPropagation()
    setIsEditing(true)
    setNewTitle(conversation.title || 'Untitled')
  }

  const handleSave = () => {
    if (newTitle.trim() && newTitle !== conversation.title) {
      updateConversation.mutate({
        id: conversation.id,
        data: { title: newTitle.trim() }
      })
    }
    setIsEditing(false)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      handleSave()
    } else if (e.key === 'Escape') {
      setIsEditing(false)
      setNewTitle(conversation.title || '')
    }
  }

  const displayTitle = conversation.title || 'New Conversation'
  const messageCount = conversation.message_count

  return (
    <div
      className={cn(
        'group relative p-3 rounded-lg cursor-pointer transition-all duration-200',
        'hover:bg-accent/50',
        isActive && 'bg-primary/10 border border-primary/20'
      )}
      onClick={onClick}
      onMouseEnter={() => setShowActions(true)}
      onMouseLeave={() => setShowActions(false)}
    >
      <div className="flex items-start gap-3">
        <div className={cn(
          'w-2 h-2 rounded-full mt-2 shrink-0',
          isActive ? 'bg-primary' : 'bg-muted-foreground/40'
        )} />

        <div className="flex-1 min-w-0">
          {isEditing ? (
            <input
              type="text"
              value={newTitle}
              onChange={(e) => setNewTitle(e.target.value)}
              onBlur={handleSave}
              onKeyDown={handleKeyDown}
              className="w-full text-sm font-medium bg-transparent border-none outline-none focus:ring-0"
              autoFocus
              onClick={(e) => e.stopPropagation()}
            />
          ) : (
            <h4 className={cn(
              'text-sm font-medium truncate',
              isActive ? 'text-primary' : 'text-foreground'
            )}>
              {truncateText(displayTitle, 40)}
            </h4>
          )}

          <div className="flex items-center gap-2 mt-1">
            <span className="text-xs text-muted-foreground">
              {formatTimeAgo(conversation.updated_at)}
            </span>

            {messageCount > 0 && (
              <>
                <span className="text-xs text-muted-foreground">•</span>
                <div className="flex items-center gap-1">
                  <MessageSquare className="w-3 h-3 text-muted-foreground" />
                  <span className="text-xs text-muted-foreground">
                    {messageCount}
                  </span>
                </div>
              </>
            )}
          </div>
        </div>

        {/* Actions */}
        {showActions && !isEditing && (
          <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
            <Button
              variant="ghost"
              size="sm"
              onClick={handleEdit}
              className="h-6 w-6 p-0"
            >
              <Edit className="w-3 h-3" />
            </Button>

            <Button
              variant="ghost"
              size="sm"
              onClick={handleDelete}
              className="h-6 w-6 p-0 text-destructive hover:text-destructive"
              disabled={deleteConversation.isPending}
            >
              <Trash2 className="w-3 h-3" />
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}

