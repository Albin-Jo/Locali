// frontend/src/components/layout/MainLayout.tsx

import React from 'react'
import { Outlet } from 'react-router-dom'
import { Header } from './Header'
import { Sidebar } from './Sidebar'
import { SearchOverlay } from '@/components/search/SearchOverlay'
import { useAppStore } from '@/store'
import { cn } from '@/lib/utils'

export function MainLayout() {
  const { sidebar, search } = useAppStore()

  return (
    <div className="flex h-screen bg-background">
      {/* Sidebar */}
      <div
        className={cn(
          'border-r border-border bg-card transition-all duration-300',
          sidebar.isCollapsed ? 'w-16' : 'w-80'
        )}
      >
        <Sidebar />
      </div>

      {/* Main Content Area */}
      <div className="flex flex-1 flex-col">
        <Header />

        <main className="flex-1 overflow-hidden">
          <Outlet />
        </main>
      </div>

      {/* Search Overlay */}
      {search.isOpen && <SearchOverlay />}
    </div>
  )
}

