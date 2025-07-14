// frontend/src/lib/api.ts

import {
  ApiError,
  NetworkError,
  type Conversation,
  type ConversationDetail,
  type Message,
  type Model,
  type SystemStatus,
  type Document,
  type DocumentDetail,
  type SearchResponse,
  type SearchStats,
  type BackgroundTask,
  type TaskList,
  type SystemHealth,
  type ModelDownload,
  type SendMessageRequest,
  type CreateConversationRequest,
  type UpdateConversationRequest,
  type SearchRequest,
  type ProcessDocumentRequest,
} from '@/types'

const BASE_URL = '/api/v1'

class ApiClient {
  private baseUrl: string

  constructor(baseUrl: string = BASE_URL) {
    this.baseUrl = baseUrl
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`

    const config: RequestInit = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    }

    try {
      const response = await fetch(url, config)

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new ApiError(
          errorData.detail || `HTTP ${response.status}: ${response.statusText}`,
          response.status,
          errorData.code
        )
      }

      // Handle empty responses
      const contentType = response.headers.get('content-type')
      if (!contentType?.includes('application/json')) {
        return {} as T
      }

      return await response.json()
    } catch (error) {
      if (error instanceof ApiError) {
        throw error
      }

      if (error instanceof TypeError && error.message.includes('fetch')) {
        throw new NetworkError('Unable to connect to the server')
      }

      throw new ApiError('An unexpected error occurred')
    }
  }

  private async streamRequest(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<ReadableStream<string>> {
    const url = `${this.baseUrl}${endpoint}`

    const config: RequestInit = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    }

    try {
      const response = await fetch(url, config)

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new ApiError(
          errorData.detail || `HTTP ${response.status}: ${response.statusText}`,
          response.status
        )
      }

      if (!response.body) {
        throw new ApiError('No response body for streaming request')
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()

      return new ReadableStream({
        start(controller) {
          function pump(): Promise<void> {
            return reader.read().then(({ done, value }) => {
              if (done) {
                controller.close()
                return
              }

              const chunk = decoder.decode(value)
              const lines = chunk.split('\n')

              for (const line of lines) {
                if (line.startsWith('data: ')) {
                  const data = line.slice(6).trim()
                  if (data === '[DONE]') {
                    controller.close()
                    return
                  }
                  if (data) {
                    controller.enqueue(data)
                  }
                }
              }

              return pump()
            })
          }

          return pump()
        }
      })
    } catch (error) {
      if (error instanceof ApiError) {
        throw error
      }
      throw new NetworkError('Failed to establish streaming connection')
    }
  }

  // Conversation API
  async getConversations(): Promise<Conversation[]> {
    return this.request<Conversation[]>('/conversations')
  }

  async getConversation(id: string): Promise<ConversationDetail> {
    return this.request<ConversationDetail>(`/conversations/${id}`)
  }

  async createConversation(data: CreateConversationRequest): Promise<Conversation> {
    return this.request<Conversation>('/conversations', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  async updateConversation(id: string, data: UpdateConversationRequest): Promise<Conversation> {
    return this.request<Conversation>(`/conversations/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    })
  }

  async deleteConversation(id: string): Promise<{ message: string }> {
    return this.request(`/conversations/${id}`, {
      method: 'DELETE',
    })
  }

  async sendMessage(conversationId: string, data: SendMessageRequest): Promise<ReadableStream<string>> {
    return this.streamRequest(`/conversations/${conversationId}/messages`, {
      method: 'POST',
      body: JSON.stringify({ ...data, stream: true }),
    })
  }

  async sendMessageSync(conversationId: string, data: SendMessageRequest): Promise<{ response: string }> {
    return this.request(`/conversations/${conversationId}/messages`, {
      method: 'POST',
      body: JSON.stringify({ ...data, stream: false }),
    })
  }

  // Model API
  async getModels(): Promise<Model[]> {
    return this.request<Model[]>('/models')
  }

  async getCurrentModel(): Promise<{ message?: string } | Model> {
    return this.request('/models/current')
  }

  async loadModel(modelName: string): Promise<{ success: boolean; message: string }> {
    return this.request('/models/load', {
      method: 'POST',
      body: JSON.stringify({ model_name: modelName }),
    })
  }

  async unloadModel(modelName: string): Promise<{ success: boolean; message: string }> {
    return this.request(`/models/unload/${modelName}`, {
      method: 'POST',
    })
  }

  async switchModel(modelName: string): Promise<{ success: boolean; message: string }> {
    return this.request(`/models/switch/${modelName}`, {
      method: 'POST',
    })
  }

  async getSystemStatus(): Promise<SystemStatus> {
    return this.request<SystemStatus>('/models/status')
  }

  async getModelRecommendations(): Promise<any> {
    return this.request('/models/recommendations')
  }

  // Document API
  async getDocuments(): Promise<Document[]> {
    return this.request<Document[]>('/documents')
  }

  async getDocument(id: string): Promise<DocumentDetail> {
    return this.request<DocumentDetail>(`/documents/${id}`)
  }

  async uploadDocument(file: File): Promise<Document> {
    const formData = new FormData()
    formData.append('file', file)

    return this.request<Document>('/documents/upload', {
      method: 'POST',
      body: formData,
      headers: {}, // Remove Content-Type header to let browser set it with boundary
    })
  }

  async processTextDocument(data: ProcessDocumentRequest): Promise<Document> {
    return this.request<Document>('/documents/process-text', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  async deleteDocument(id: string): Promise<{ message: string }> {
    return this.request(`/documents/${id}`, {
      method: 'DELETE',
    })
  }

  // Search API
  async search(data: SearchRequest): Promise<SearchResponse> {
    return this.request<SearchResponse>('/search', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  async searchGet(query: string, options?: Partial<SearchRequest>): Promise<SearchResponse> {
    const params = new URLSearchParams({ q: query })
    if (options?.max_results) params.append('max_results', options.max_results.toString())
    if (options?.vector_weight) params.append('vector_weight', options.vector_weight.toString())
    if (options?.keyword_weight) params.append('keyword_weight', options.keyword_weight.toString())
    if (options?.min_score) params.append('min_score', options.min_score.toString())

    return this.request<SearchResponse>(`/search?${params}`)
  }

  async getSearchStats(): Promise<SearchStats> {
    return this.request<SearchStats>('/search/stats')
  }

  // System API
  async getSystemHealth(): Promise<SystemHealth> {
    return this.request<SystemHealth>('/system/health')
  }

  async getSystemSummary(): Promise<any> {
    return this.request('/system/summary')
  }

  async getPerformanceMetrics(): Promise<any> {
    return this.request('/system/performance')
  }

  async startPerformanceMonitoring(intervalSeconds: number = 30): Promise<{ message: string }> {
    return this.request('/system/performance/start', {
      method: 'POST',
      body: JSON.stringify({ interval_seconds: intervalSeconds }),
    })
  }

  async stopPerformanceMonitoring(): Promise<{ message: string }> {
    return this.request('/system/performance/stop', {
      method: 'POST',
    })
  }

  async getModelRepository(): Promise<{ models: ModelDownload[] }> {
    return this.request('/system/models/repository')
  }

  async downloadModel(modelName: string): Promise<ReadableStream<string>> {
    return this.streamRequest('/system/models/download', {
      method: 'POST',
      body: JSON.stringify({ model_name: modelName }),
    })
  }

  async getDownloadStatus(modelName: string): Promise<any> {
    return this.request(`/system/models/download/${modelName}/status`)
  }

  async cancelDownload(modelName: string): Promise<{ message: string }> {
    return this.request(`/system/models/download/${modelName}/cancel`, {
      method: 'POST',
    })
  }

  // Tasks API
  async getTasks(status?: string): Promise<TaskList> {
    const params = status ? `?status=${status}` : ''
    return this.request<TaskList>(`/tasks${params}`)
  }

  async getTask(taskId: string): Promise<BackgroundTask> {
    return this.request<BackgroundTask>(`/tasks/${taskId}`)
  }

  async cancelTask(taskId: string): Promise<{ message: string }> {
    return this.request(`/tasks/${taskId}/cancel`, {
      method: 'POST',
    })
  }

  async getTaskStats(): Promise<any> {
    return this.request('/tasks/stats/summary')
  }

  // Health and status endpoints
  async getApiStatus(): Promise<any> {
    return this.request('/status')
  }

  async getCapabilities(): Promise<any> {
    return this.request('/capabilities')
  }

  async getHealth(): Promise<any> {
    return this.request('/../health') // Goes to root /health endpoint
  }
}

// Create singleton instance
export const api = new ApiClient()

// Utility functions for handling streaming responses
export async function* streamToAsyncGenerator(stream: ReadableStream<string>) {
  const reader = stream.getReader()

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      yield value
    }
  } finally {
    reader.releaseLock()
  }
}

export function createStreamingMessageHandler(
  onToken: (token: string) => void,
  onComplete: () => void,
  onError: (error: Error) => void
) {
  return async (stream: ReadableStream<string>) => {
    try {
      for await (const token of streamToAsyncGenerator(stream)) {
        onToken(token)
      }
      onComplete()
    } catch (error) {
      onError(error instanceof Error ? error : new Error('Streaming error'))
    }
  }
}

// Rate limiting helper
export class RateLimiter {
  private requests: number[] = []
  private maxRequests: number
  private windowMs: number

  constructor(maxRequests: number, windowMs: number) {
    this.maxRequests = maxRequests
    this.windowMs = windowMs
  }

  canMakeRequest(): boolean {
    const now = Date.now()

    // Remove old requests outside the window
    this.requests = this.requests.filter(time => now - time < this.windowMs)

    if (this.requests.length >= this.maxRequests) {
      return false
    }

    this.requests.push(now)
    return true
  }

  getTimeUntilNextRequest(): number {
    if (this.requests.length < this.maxRequests) {
      return 0
    }

    const oldestRequest = Math.min(...this.requests)
    return Math.max(0, this.windowMs - (Date.now() - oldestRequest))
  }
}

// Create rate limiter for API requests (100 requests per minute)
export const apiRateLimiter = new RateLimiter(100, 60 * 1000)

// Export default API client
export default api