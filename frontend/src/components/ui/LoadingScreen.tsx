// frontend/src/components/ui/LoadingScreen.tsx

import React from 'react'
import { Cpu, Loader2 } from 'lucide-react'

export function LoadingScreen() {
  return (
    <div className="min-h-screen bg-background flex items-center justify-center">
      <div className="text-center">
        <div className="flex items-center justify-center mb-4">
          <div className="w-12 h-12 rounded-full bg-primary flex items-center justify-center">
            <Cpu className="w-6 h-6 text-primary-foreground" />
          </div>
        </div>

        <h1 className="text-2xl font-semibold text-foreground mb-2">Locali</h1>
        <p className="text-muted-foreground mb-4">Starting your AI coding assistant...</p>

        <div className="flex items-center justify-center">
          <Loader2 className="w-5 h-5 animate-spin text-primary" />
        </div>
      </div>
    </div>
  )
}

