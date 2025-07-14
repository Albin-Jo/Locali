// frontend/src/pages/SettingsPage.tsx

import React from 'react'
import {
  Cpu,
  Shield,
  Palette,
  Database,
  Network,
  Bell,
  Download,
  Info,
  AlertCircle,
  CheckCircle
} from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { useSystemStatus, useSystemHealth } from '@/lib/queries'
import { useAppStore, appActions } from '@/store'
import { formatFileSize } from '@/lib/utils'
import { cn } from '@/lib/utils'

export function SettingsPage() {
  const { settings, features } = useAppStore()
  const { data: systemStatus } = useSystemStatus()
  const { data: systemHealth } = useSystemHealth()

  const sections = [
    {
      id: 'model',
      title: 'Model Settings',
      icon: Cpu,
      description: 'Configure AI model parameters'
    },
    {
      id: 'security',
      title: 'Security & Privacy',
      icon: Shield,
      description: 'Privacy and security settings'
    },
    {
      id: 'appearance',
      title: 'Appearance',
      icon: Palette,
      description: 'Theme and display preferences'
    },
    {
      id: 'system',
      title: 'System Info',
      icon: Database,
      description: 'Performance and diagnostics'
    }
  ]

  const [activeSection, setActiveSection] = React.useState('model')

  return (
    <div className="h-full flex">
      {/* Sidebar */}
      <div className="w-80 border-r border-border bg-card">
        <div className="p-6 border-b border-border">
          <h1 className="text-xl font-semibold text-foreground">Settings</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Configure your AI assistant
          </p>
        </div>

        <div className="p-4">
          {sections.map(section => {
            const Icon = section.icon
            return (
              <button
                key={section.id}
                onClick={() => setActiveSection(section.id)}
                className={cn(
                  'w-full text-left p-3 rounded-lg transition-colors mb-2',
                  'hover:bg-accent hover:text-accent-foreground',
                  activeSection === section.id && 'bg-primary/10 border border-primary/20'
                )}
              >
                <div className="flex items-center gap-3">
                  <Icon className="w-5 h-5" />
                  <div>
                    <div className="font-medium">{section.title}</div>
                    <div className="text-xs text-muted-foreground">{section.description}</div>
                  </div>
                </div>
              </button>
            )
          })}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-4xl mx-auto p-8">
          {activeSection === 'model' && (
            <ModelSettings settings={settings} onUpdate={appActions.updateSettings} />
          )}
          {activeSection === 'security' && (
            <SecuritySettings features={features} onUpdate={appActions.updateSettings} />
          )}
          {activeSection === 'appearance' && (
            <AppearanceSettings settings={settings} onUpdate={appActions.updateSettings} />
          )}
          {activeSection === 'system' && (
            <SystemInfo systemStatus={systemStatus} systemHealth={systemHealth} />
          )}
        </div>
      </div>
    </div>
  )
}

// Settings sections
function ModelSettings({ settings, onUpdate }: any) {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-foreground mb-2">Model Configuration</h2>
        <p className="text-muted-foreground">Adjust AI model behavior and performance</p>
      </div>

      <div className="space-y-4">
        <div>
          <label className="text-sm font-medium text-foreground block mb-2">
            Temperature ({settings.temperature})
          </label>
          <input
            type="range"
            min="0"
            max="2"
            step="0.1"
            value={settings.temperature}
            onChange={(e) => onUpdate({ temperature: parseFloat(e.target.value) })}
            className="w-full"
          />
          <div className="flex justify-between text-xs text-muted-foreground mt-1">
            <span>More focused</span>
            <span>More creative</span>
          </div>
        </div>

        <div>
          <label className="text-sm font-medium text-foreground block mb-2">
            Max Tokens ({settings.maxTokens})
          </label>
          <input
            type="range"
            min="256"
            max="4096"
            step="256"
            value={settings.maxTokens}
            onChange={(e) => onUpdate({ maxTokens: parseInt(e.target.value) })}
            className="w-full"
          />
          <div className="flex justify-between text-xs text-muted-foreground mt-1">
            <span>Shorter responses</span>
            <span>Longer responses</span>
          </div>
        </div>
      </div>
    </div>
  )
}

function SecuritySettings({ features, onUpdate }: any) {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-foreground mb-2">Security & Privacy</h2>
        <p className="text-muted-foreground">Control how your data is handled</p>
      </div>

      <div className="space-y-4">
        <div className="flex items-center justify-between p-4 border border-border rounded-lg">
          <div>
            <h3 className="font-medium text-foreground">Network Isolation</h3>
            <p className="text-sm text-muted-foreground">Block all network access for privacy</p>
          </div>
          <div className="flex items-center gap-2">
            {features.networkIsolation ? (
              <CheckCircle className="w-5 h-5 text-green-500" />
            ) : (
              <AlertCircle className="w-5 h-5 text-yellow-500" />
            )}
            <span className="text-sm font-medium">
              {features.networkIsolation ? 'Enabled' : 'Disabled'}
            </span>
          </div>
        </div>

        <div className="flex items-center justify-between p-4 border border-border rounded-lg">
          <div>
            <h3 className="font-medium text-foreground">Conversation Encryption</h3>
            <p className="text-sm text-muted-foreground">Encrypt stored conversations</p>
          </div>
          <div className="flex items-center gap-2">
            {features.encryption ? (
              <CheckCircle className="w-5 h-5 text-green-500" />
            ) : (
              <AlertCircle className="w-5 h-5 text-yellow-500" />
            )}
            <span className="text-sm font-medium">
              {features.encryption ? 'Enabled' : 'Disabled'}
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}

function AppearanceSettings({ settings, onUpdate }: any) {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-foreground mb-2">Appearance</h2>
        <p className="text-muted-foreground">Customize the look and feel</p>
      </div>

      <div className="space-y-4">
        <div>
          <label className="text-sm font-medium text-foreground block mb-2">Theme</label>
          <div className="flex gap-2">
            <Button
              variant={settings.theme === 'dark' ? 'default' : 'outline'}
              onClick={() => {
                onUpdate({ theme: 'dark' })
                appActions.setTheme('dark')
              }}
            >
              Dark
            </Button>
            <Button
              variant={settings.theme === 'light' ? 'default' : 'outline'}
              onClick={() => {
                onUpdate({ theme: 'light' })
                appActions.setTheme('light')
              }}
            >
              Light
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}

function SystemInfo({ systemStatus, systemHealth }: any) {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-foreground mb-2">System Information</h2>
        <p className="text-muted-foreground">Performance metrics and diagnostics</p>
      </div>

      {systemStatus && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="p-4 border border-border rounded-lg">
            <h3 className="font-medium text-foreground mb-2">Memory Usage</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Total RAM</span>
                <span>{systemStatus.system.ram_gb}GB</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Available</span>
                <span>{Math.round(systemStatus.memory.system_available_mb / 1024)}GB</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Used by Models</span>
                <span>{Math.round(systemStatus.memory.used_by_models_mb / 1024)}GB</span>
              </div>
            </div>
          </div>

          <div className="p-4 border border-border rounded-lg">
            <h3 className="font-medium text-foreground mb-2">Models</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Current Model</span>
                <span>{systemStatus.models.current || 'None'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Loaded</span>
                <span>{systemStatus.models.count}</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {systemHealth && (
        <div className="space-y-3">
          <h3 className="font-medium text-foreground">System Health</h3>
          {Object.entries(systemHealth.checks).map(([key, check]: [string, any]) => (
            <div key={key} className="flex items-center justify-between p-3 border border-border rounded-lg">
              <span className="text-sm font-medium capitalize">{key.replace('_', ' ')}</span>
              <div className="flex items-center gap-2">
                {check.status === 'ok' ? (
                  <CheckCircle className="w-4 h-4 text-green-500" />
                ) : (
                  <AlertCircle className="w-4 h-4 text-yellow-500" />
                )}
                <span className="text-sm">{check.status}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}