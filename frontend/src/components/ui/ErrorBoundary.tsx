// frontend/src/components/ui/ErrorBoundary.tsx

import React from 'react'
import { AlertTriangle, RefreshCw } from 'lucide-react'
import { Button } from './Button'

interface ErrorBoundaryState {
  hasError: boolean
  error?: Error
}

export class ErrorBoundary extends React.Component<
  { children: React.ReactNode },
  ErrorBoundaryState
> {
  constructor(props: { children: React.ReactNode }) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('Error caught by boundary:', error, errorInfo)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-background flex items-center justify-center">
          <div className="text-center max-w-md">
            <div className="flex items-center justify-center mb-4">
              <AlertTriangle className="w-12 h-12 text-destructive" />
            </div>

            <h1 className="text-xl font-semibold text-foreground mb-2">
              Something went wrong
            </h1>

            <p className="text-muted-foreground mb-4">
              An unexpected error occurred. Try refreshing the page.
            </p>

            {this.state.error && (
              <details className="text-xs text-left bg-card border border-border rounded p-3 mb-4">
                <summary className="cursor-pointer text-muted-foreground">
                  Error details
                </summary>
                <pre className="mt-2 text-destructive whitespace-pre-wrap">
                  {this.state.error.message}
                </pre>
              </details>
            )}

            <Button onClick={() => window.location.reload()}>
              <RefreshCw className="w-4 h-4 mr-2" />
              Refresh Page
            </Button>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}

