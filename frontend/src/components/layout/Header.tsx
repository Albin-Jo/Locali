// frontend/src/components/layout/Header.tsx

import React from 'react'
import {
  Settings,
  Search,
  Plus,
  Cpu,
  Wifi,
  WifiOff,
  Activity
} from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { ModelSelector } from '@/components/models/ModelSelector'
import { StatusIndicator } from '@/components/system/StatusIndicator'
import { useAppStore, appActions } from '@/store'
import { useCreateConversation, useSystemStatus } from '@/lib/queries'

export function Header() {
  const { currentModelName, features } = useAppStore()
  const { data: systemStatus } = useSystemStatus()
  const createConversation = useCreateConversation()

  const handleNewChat = () => {
    createConversation.mutate({
      model_name: currentModelName,
    })
  }

  const handleSearchToggle = () => {
    appActions.openSearch()
  }

  return (
    <header className="h-16 border-b border-border bg-card px-6 flex items-center justify-between">
      {/* Left side - Logo and title */}
      <div className="flex items-center space-x-4">
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center">
            <Cpu className="w-4 h-4 text-primary-foreground" />
          </div>
          <div>
            <h1 className="text-lg font-semibold text-foreground">Locali</h1>
            <p className="text-xs text-muted-foreground">AI Coding Assistant</p>
          </div>
        </div>
      </div>

      {/* Center - Actions */}
      <div className="flex items-center space-x-2">
        <Button
          variant="outline"
          size="sm"
          onClick={handleNewChat}
          disabled={createConversation.isPending}
        >
          <Plus className="w-4 h-4 mr-2" />
          New Chat
        </Button>

        <Button
          variant="ghost"
          size="sm"
          onClick={handleSearchToggle}
        >
          <Search className="w-4 h-4 mr-2" />
          Search
          <kbd className="ml-2 px-1.5 py-0.5 text-xs bg-muted border rounded">
            ⌘K
          </kbd>
        </Button>
      </div>

      {/* Right side - Model selector and status */}
      <div className="flex items-center space-x-4">
        <ModelSelector />

        <div className="flex items-center space-x-2">
          <StatusIndicator
            icon={features.networkIsolation ? WifiOff : Wifi}
            status={features.networkIsolation ? 'offline' : 'online'}
            tooltip={features.networkIsolation ? 'Network Isolated' : 'Network Connected'}
          />

          <StatusIndicator
            icon={Activity}
            status={systemStatus?.memory.system_available_mb > 2000 ? 'good' : 'warning'}
            tooltip={`${Math.round((systemStatus?.memory.system_available_mb || 0) / 1024)}GB RAM available`}
          />
        </div>

        <Button variant="ghost" size="sm">
          <Settings className="w-4 h-4" />
        </Button>
      </div>
    </header>
  )
}

