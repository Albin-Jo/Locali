// frontend/src/components/layout/Sidebar.tsx

import React from 'react'
import {
  MessageSquare,
  FileText,
  Settings,
  ChevronLeft,
  ChevronRight,
  Plus
} from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { ConversationList } from '@/components/conversations/ConversationList'
import { DocumentList } from '@/components/documents/DocumentList'
import { WorkspaceSection } from '@/components/workspace/WorkspaceSection'
import { useAppStore, appActions } from '@/store'
import { cn } from '@/lib/utils'

const sidebarSections = [
  { id: 'conversations', label: 'Conversations', icon: MessageSquare },
  { id: 'documents', label: 'Documents', icon: FileText },
  { id: 'settings', label: 'Settings', icon: Settings },
] as const

export function Sidebar() {
  const { sidebar } = useAppStore()

  const toggleSidebar = () => {
    appActions.toggleSidebar()
  }

  const setActiveSection = (section: typeof sidebar.activeSection) => {
    appActions.setSidebarSection(section)
  }

  return (
    <div className="h-full flex flex-col">
      {/* Sidebar Header */}
      <div className="p-4 border-b border-border flex items-center justify-between">
        {!sidebar.isCollapsed && (
          <h2 className="font-semibold text-foreground">
            {sidebarSections.find(s => s.id === sidebar.activeSection)?.label}
          </h2>
        )}

        <Button
          variant="ghost"
          size="sm"
          onClick={toggleSidebar}
          className="ml-auto"
        >
          {sidebar.isCollapsed ? (
            <ChevronRight className="w-4 h-4" />
          ) : (
            <ChevronLeft className="w-4 h-4" />
          )}
        </Button>
      </div>

      {/* Section Tabs */}
      {!sidebar.isCollapsed && (
        <div className="flex border-b border-border">
          {sidebarSections.map((section) => {
            const Icon = section.icon
            return (
              <button
                key={section.id}
                onClick={() => setActiveSection(section.id)}
                className={cn(
                  'flex-1 flex items-center justify-center px-3 py-2 text-sm font-medium transition-colors',
                  'hover:bg-accent hover:text-accent-foreground',
                  sidebar.activeSection === section.id
                    ? 'border-b-2 border-primary text-primary'
                    : 'text-muted-foreground'
                )}
              >
                <Icon className="w-4 h-4 mr-2" />
                {section.label}
              </button>
            )
          })}
        </div>
      )}

      {/* Section Content */}
      <div className="flex-1 overflow-hidden">
        {sidebar.isCollapsed ? (
          <div className="flex flex-col items-center py-4 space-y-2">
            {sidebarSections.map((section) => {
              const Icon = section.icon
              return (
                <Button
                  key={section.id}
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    setActiveSection(section.id)
                    appActions.toggleSidebar() // Expand when clicked
                  }}
                  className={cn(
                    'w-10 h-10 p-0',
                    sidebar.activeSection === section.id && 'bg-accent'
                  )}
                >
                  <Icon className="w-4 h-4" />
                </Button>
              )
            })}
          </div>
        ) : (
          <div className="h-full flex flex-col">
            {sidebar.activeSection === 'conversations' && (
              <ConversationList />
            )}
            {sidebar.activeSection === 'documents' && (
              <DocumentList />
            )}
            {sidebar.activeSection === 'settings' && (
              <div className="p-4">
                <p className="text-sm text-muted-foreground">
                  Settings panel coming soon...
                </p>
              </div>
            )}

            {/* Workspace Section */}
            <WorkspaceSection />
          </div>
        )}
      </div>
    </div>
  )
}

