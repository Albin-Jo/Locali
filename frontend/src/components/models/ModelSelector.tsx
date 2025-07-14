// frontend/src/components/models/ModelSelector.tsx

import React, { useState } from 'react'
import { Cpu, ChevronDown, Check, Loader2, Download } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { useModels, useSystemStatus, useSwitchModel } from '@/lib/queries'
import { useAppStore } from '@/store'
import { cn } from '@/lib/utils'
import { formatFileSize } from '@/lib/utils'

export function ModelSelector() {
  const [isOpen, setIsOpen] = useState(false)
  const { data: models } = useModels()
  const { data: systemStatus } = useSystemStatus()
  const { currentModelName } = useAppStore()
  const switchModel = useSwitchModel()

  const currentModel = models?.find(m => m.name === currentModelName)
  const availableModels = models?.filter(m => m.exists) || []
  const loadedModels = models?.filter(m => m.loaded) || []

  const handleModelSwitch = (modelName: string) => {
    if (modelName === currentModelName) return

    switchModel.mutate(modelName)
    setIsOpen(false)
  }

  return (
    <div className="relative">
      <Button
        variant="outline"
        onClick={() => setIsOpen(!isOpen)}
        className="min-w-[160px] justify-between"
        disabled={switchModel.isPending}
      >
        <div className="flex items-center gap-2">
          <Cpu className="w-4 h-4" />
          <span className="text-sm">
            {currentModel?.name || 'No model'}
          </span>
          {switchModel.isPending && (
            <Loader2 className="w-3 h-3 animate-spin" />
          )}
        </div>
        <ChevronDown className="w-4 h-4" />
      </Button>

      {isOpen && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 z-10"
            onClick={() => setIsOpen(false)}
          />

          {/* Dropdown */}
          <div className="absolute top-full left-0 mt-2 w-80 bg-popover border border-border rounded-lg shadow-lg z-20">
            <div className="p-3 border-b border-border">
              <h3 className="font-medium text-sm">Select Model</h3>
              <p className="text-xs text-muted-foreground mt-1">
                {systemStatus?.memory.available_mb &&
                  `${Math.round(systemStatus.memory.available_mb / 1024)}GB RAM available`
                }
              </p>
            </div>

            <div className="p-1 max-h-60 overflow-y-auto">
              {availableModels.length === 0 ? (
                <div className="p-3 text-center text-muted-foreground text-sm">
                  No models available
                </div>
              ) : (
                availableModels.map(model => (
                  <button
                    key={model.name}
                    onClick={() => handleModelSwitch(model.name)}
                    disabled={switchModel.isPending}
                    className={cn(
                      'w-full text-left p-3 rounded-md transition-colors',
                      'hover:bg-accent hover:text-accent-foreground',
                      'disabled:opacity-50 disabled:cursor-not-allowed',
                      model.loaded && 'bg-primary/10 border border-primary/20'
                    )}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-sm">
                            {model.name}
                          </span>

                          {model.loaded && (
                            <div className="flex items-center gap-1">
                              <div className="w-2 h-2 bg-green-500 rounded-full" />
                              <span className="text-xs text-green-600">Loaded</span>
                            </div>
                          )}

                          {model.name === currentModelName && (
                            <Check className="w-4 h-4 text-primary" />
                          )}
                        </div>

                        <div className="flex items-center gap-2 mt-1 text-xs text-muted-foreground">
                          <span>{formatFileSize(model.size_mb * 1024 * 1024)}</span>

                          {model.memory_usage_mb && (
                            <>
                              <span>•</span>
                              <span>{Math.round(model.memory_usage_mb / 1024)}GB RAM</span>
                            </>
                          )}
                        </div>
                      </div>
                    </div>
                  </button>
                ))
              )}
            </div>

            {/* Footer */}
            <div className="p-3 border-t border-border">
              <Button
                variant="ghost"
                size="sm"
                className="w-full justify-start"
                onClick={() => {
                  setIsOpen(false)
                  // Navigate to model management
                }}
              >
                <Download className="w-4 h-4 mr-2" />
                Download More Models
              </Button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

