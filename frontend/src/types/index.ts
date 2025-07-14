// frontend/src/types/index.ts

export interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: string
  tokens?: number
  metadata?: Record<string, any>
}

export interface Conversation {
  id: string
  title?: string
  message_count: number
  model_name?: string
  created_at: string
  updated_at: string
}

export interface ConversationDetail {
  id: string
  title?: string
  messages: Message[]
  model_name?: string
  created_at: string
  updated_at: string
}

export interface Model {
  name: string
  loaded: boolean
  exists: boolean
  size_mb: number
  memory_usage_mb?: number
  config: Record<string, any>
  path: string
}

export interface ModelInfo {
  name: string
  loaded: boolean
  memory_usage_mb: number
  config: Record<string, any>
  path: string
}

export interface SystemStatus {
  system: {
    ram_gb: number
    cpu_count: number
    platform: string
    architecture: string
    gpu?: {
      name: string
      memory_mb?: number
      type: string
    }
  }
  memory: {
    total_mb: number
    used_by_models_mb: number
    available_mb: number
    system_available_mb: number
  }
  models: {
    loaded: string[]
    current?: string
    count: number
  }
  recommendations: {
    recommended_model: string
    reason: string
    gpu_optimization?: string
  }
}

export interface Document {
  id: string
  filename: string
  content_type: string
  size_bytes: number
  total_chunks: number
  processed_at: string
}

export interface DocumentDetail {
  id: string
  filename: string
  content_type: string
  size_bytes: number
  chunks: DocumentChunk[]
  metadata: Record<string, any>
  processed_at: string
}

export interface DocumentChunk {
  id: string
  document_id: string
  content: string
  metadata: Record<string, any>
  position: number
  chunk_type: string
  language?: string
  embedding?: number[]
}

export interface SearchResult {
  chunk_id: string
  document_id: string
  content: string
  score: number
  rank: number
  metadata: Record<string, any>
  chunk_type: string
  language?: string
}

export interface SearchResponse {
  query: string
  results: SearchResult[]
  total_results: number
  search_time_ms: number
}

export interface SearchStats {
  total_chunks: number
  vector_store_size: number
  keyword_index_size: number
  embedding_model: string
}

export interface BackgroundTask {
  task_id: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
  progress: number
  result?: any
  error?: string
  created_at: string
  started_at?: string
  completed_at?: string
  metadata: Record<string, any>
}

export interface TaskList {
  tasks: BackgroundTask[]
  total_count: number
  running_count: number
  completed_count: number
  failed_count: number
}

export interface SystemHealth {
  overall_status: string
  timestamp: string
  checks: Record<string, {
    status: string
    details: Record<string, any>
  }>
}

export interface ModelDownload {
  name: string
  display_name: string
  size_gb: number
  description: string
  requirements: {
    min_ram_gb: number
    recommended_ram_gb: number
    gpu_recommended: boolean
  }
  tags: string[]
  installed: boolean
  installing: boolean
  compatible: boolean
  download_progress?: {
    status: string
    downloaded_bytes: number
    total_bytes: number
    progress_percent: number
    speed_mbps: number
    eta_seconds: number
  }
}

export interface ApiResponse<T = any> {
  data?: T
  error?: string
  message?: string
}

export interface StreamingMessage {
  content: string
  isComplete: boolean
  error?: string
}

// API Request types
export interface SendMessageRequest {
  message: string
  model_name?: string
  stream?: boolean
  temperature?: number
  max_tokens?: number
}

export interface CreateConversationRequest {
  title?: string
  model_name?: string
}

export interface UpdateConversationRequest {
  title: string
}

export interface SearchRequest {
  query: string
  max_results?: number
  vector_weight?: number
  keyword_weight?: number
  min_score?: number
}

export interface ProcessDocumentRequest {
  content: string
  filename: string
  content_type?: string
}

// UI State types
export interface AppState {
  currentConversation?: string
  conversations: Conversation[]
  models: Model[]
  currentModel?: string
  documents: Document[]
  isLoading: boolean
  error?: string
}

export interface ChatState {
  messages: Message[]
  isStreaming: boolean
  currentResponse: string
  error?: string
}

export interface SidebarState {
  isCollapsed: boolean
  activeSection: 'conversations' | 'documents' | 'settings'
}

export interface SearchState {
  isOpen: boolean
  query: string
  results: SearchResult[]
  isSearching: boolean
}

export interface SettingsState {
  model: string
  temperature: number
  maxTokens: number
  theme: 'dark' | 'light'
  networkIsolation: boolean
  encryption: boolean
}

// Event types for WebSocket/SSE
export interface StreamEvent {
  type: 'token' | 'error' | 'complete'
  data: string
}

export interface SystemEvent {
  type: 'model_loaded' | 'model_unloaded' | 'task_update' | 'health_change'
  data: any
}

// Utility types
export type LoadingState = 'idle' | 'loading' | 'success' | 'error'

export interface AsyncState<T> {
  data?: T
  status: LoadingState
  error?: string
}

// Component prop types
export interface MessageProps {
  message: Message
  isStreaming?: boolean
  onCopy?: (content: string) => void
  onInsert?: (content: string) => void
  onExplain?: (content: string) => void
}

export interface ConversationItemProps {
  conversation: Conversation
  isActive: boolean
  onClick: () => void
  onDelete: () => void
}

export interface ModelSelectorProps {
  models: Model[]
  currentModel?: string
  onModelChange: (modelName: string) => void
  isLoading?: boolean
}

export interface DocumentUploadProps {
  onUpload: (files: File[]) => void
  isUploading?: boolean
  maxFiles?: number
  accept?: string[]
}

export interface SearchBarProps {
  onSearch: (query: string) => void
  onClose: () => void
  placeholder?: string
  isSearching?: boolean
}

// Error types
export class ApiError extends Error {
  constructor(
    message: string,
    public status?: number,
    public code?: string
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

export class NetworkError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'NetworkError'
  }
}

// Constants
export const MESSAGE_ROLES = {
  USER: 'user' as const,
  ASSISTANT: 'assistant' as const,
  SYSTEM: 'system' as const,
}

export const TASK_STATUS = {
  PENDING: 'pending' as const,
  RUNNING: 'running' as const,
  COMPLETED: 'completed' as const,
  FAILED: 'failed' as const,
  CANCELLED: 'cancelled' as const,
}

export const LOADING_STATES = {
  IDLE: 'idle' as const,
  LOADING: 'loading' as const,
  SUCCESS: 'success' as const,
  ERROR: 'error' as const,
}

// File type definitions
export const SUPPORTED_FILE_TYPES = {
  CODE: ['.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.cpp', '.c', '.rs', '.go', '.php', '.rb', '.swift', '.kt'],
  DOCS: ['.md', '.txt', '.json', '.yaml', '.yml'],
  ALL: ['.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.cpp', '.c', '.rs', '.go', '.php', '.rb', '.swift', '.kt', '.md', '.txt', '.json', '.yaml', '.yml']
} as const

export const FILE_SIZE_LIMITS = {
  MAX_FILE_SIZE: 50 * 1024 * 1024, // 50MB
  MAX_FILES: 10,
} as const