// frontend/src/components/workspace/WorkspaceSection.tsx

import React from 'react'
import { Folder, FileText, BarChart3 } from 'lucide-react'
import { useDocuments, useSearchStats } from '@/lib/queries'
import { cn } from '@/lib/utils'

export function WorkspaceSection() {
  const { data: documents } = useDocuments()
  const { data: searchStats } = useSearchStats()

  const stats = [
    {
      icon: Folder,
      label: 'Project Files',
      value: documents?.length || 0,
      description: 'Documents indexed'
    },
    {
      icon: FileText,
      label: 'Code Chunks',
      value: searchStats?.total_chunks || 0,
      description: 'Searchable pieces'
    },
    {
      icon: BarChart3,
      label: 'Vector Store',
      value: searchStats?.vector_store_size || 0,
      description: 'Embeddings ready'
    }
  ]

  return (
    <div className="mt-auto border-t border-border p-4">
      <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">
        Workspace
      </h3>

      <div className="space-y-2">
        {stats.map((stat) => {
          const Icon = stat.icon
          return (
            <div
              key={stat.label}
              className="flex items-center gap-3 p-2 rounded-lg hover:bg-accent/50 transition-colors cursor-pointer"
            >
              <Icon className="w-4 h-4 text-muted-foreground" />
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-foreground">
                    {stat.label}
                  </span>
                  <span className="text-sm font-semibold text-primary">
                    {stat.value}
                  </span>
                </div>
                <p className="text-xs text-muted-foreground">
                  {stat.description}
                </p>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}