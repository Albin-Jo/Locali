// frontend/src/App.tsx

import React, { useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { MainLayout } from '@/components/layout/MainLayout'
import { ChatPage } from '@/pages/ChatPage'
import { DocumentsPage } from '@/pages/DocumentsPage'
import { SettingsPage } from '@/pages/SettingsPage'
import { useSystemHealth, useModels, useConversations } from '@/lib/queries'
import { appActions } from '@/store'
import { ErrorBoundary } from '@/components/ui/ErrorBoundary'
import { LoadingScreen } from '@/components/ui/LoadingScreen'
import { useKeyboardShortcuts } from '@/hooks/useKeyboardShortcuts'

function App() {
  const { data: health, isLoading: healthLoading } = useSystemHealth()
  const { data: models, isLoading: modelsLoading } = useModels()
  const { data: conversations, isLoading: conversationsLoading } = useConversations()

  // Initialize keyboard shortcuts
  useKeyboardShortcuts()

  const isInitializing = healthLoading || modelsLoading || conversationsLoading

  useEffect(() => {
    // Initialize app once all initial data is loaded
    if (!isInitializing) {
      appActions.setInitialized(true)

      // Set current model from loaded models
      if (models && models.length > 0) {
        const currentModel = models.find(m => m.loaded)
        if (currentModel) {
          appActions.setCurrentModel(currentModel.name)
        }
      }
    }
  }, [isInitializing, models])

  if (isInitializing) {
    return <LoadingScreen />
  }

  return (
    <ErrorBoundary>
      <Router>
        <div className="min-h-screen bg-background text-foreground">
          <Routes>
            <Route path="/" element={<MainLayout />}>
              <Route index element={<Navigate to="/chat" replace />} />
              <Route path="chat" element={<ChatPage />} />
              <Route path="chat/:conversationId" element={<ChatPage />} />
              <Route path="documents" element={<DocumentsPage />} />
              <Route path="settings" element={<SettingsPage />} />
            </Route>
          </Routes>
        </div>
      </Router>
    </ErrorBoundary>
  )
}

export default App