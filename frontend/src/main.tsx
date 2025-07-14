// frontend/src/main.tsx

import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import { Toaster } from 'react-hot-toast'
import App from './App'
import { loadPersistedSettings } from './store'
import './index.css'

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      retry: (failureCount, error: any) => {
        if (error?.status === 404 || error?.status === 401) {
          return false
        }
        return failureCount < 3
      },
    },
    mutations: {
      retry: (failureCount, error: any) => {
        if (error?.status === 404 || error?.status === 401) {
          return false
        }
        return failureCount < 2
      },
    },
  },
})

// Load persisted settings
loadPersistedSettings()

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
      <Toaster
        position="top-right"
        toastOptions={{
          duration: 4000,
          style: {
            background: 'hsl(var(--card))',
            color: 'hsl(var(--card-foreground))',
            border: '1px solid hsl(var(--border))',
          },
        }}
      />
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  </React.StrictMode>,
)

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

function App() {
  const { data: health, isLoading: healthLoading } = useSystemHealth()
  const { data: models, isLoading: modelsLoading } = useModels()
  const { data: conversations, isLoading: conversationsLoading } = useConversations()

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

