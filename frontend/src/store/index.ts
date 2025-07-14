// frontend/src/store/index.ts

import { proxy, useSnapshot } from 'valtio'
import { subscribeKey } from 'valtio/utils'
import type {
  Conversation,
  Message,
  Model,
  Document,
  SearchResult,
  SidebarState,
  SearchState,
  SettingsState,
  LoadingState,
} from '@/types'

// Global app state
interface AppStore {
  // UI State
  sidebar: SidebarState
  search: SearchState
  settings: SettingsState

  // Current selections
  currentConversationId?: string
  currentModelName?: string

  // Loading states
  isAppLoading: boolean
  isInitialized: boolean

  // Error state
  globalError?: string

  // Theme and preferences
  theme: 'dark' | 'light'

  // Feature flags
  features: {
    networkIsolation: boolean
    encryption: boolean
    performanceMonitoring: boolean
  }
}

// Chat state for current conversation
interface ChatStore {
  messages: Message[]
  isStreaming: boolean
  currentResponse: string
  isLoading: boolean
  error?: string

  // Input state
  inputValue: string
  isComposing: boolean

  // Message actions
  selectedMessages: Set<string>
  editingMessageId?: string
}

// Document management state
interface DocumentStore {
  uploadQueue: File[]
  uploadProgress: Record<string, number>
  isUploading: boolean
  processingDocuments: Set<string>
  lastUploadedDocument?: Document
}

// Create stores
export const appStore = proxy<AppStore>({
  sidebar: {
    isCollapsed: false,
    activeSection: 'conversations',
  },
  search: {
    isOpen: false,
    query: '',
    results: [],
    isSearching: false,
  },
  settings: {
    model: 'qwen2.5-coder-7b',
    temperature: 0.3,
    maxTokens: 2048,
    theme: 'dark',
    networkIsolation: true,
    encryption: false,
  },
  isAppLoading: false,
  isInitialized: false,
  theme: 'dark',
  features: {
    networkIsolation: true,
    encryption: false,
    performanceMonitoring: false,
  },
})

export const chatStore = proxy<ChatStore>({
  messages: [],
  isStreaming: false,
  currentResponse: '',
  isLoading: false,
  inputValue: '',
  isComposing: false,
  selectedMessages: new Set(),
})

export const documentStore = proxy<DocumentStore>({
  uploadQueue: [],
  uploadProgress: {},
  isUploading: false,
  processingDocuments: new Set(),
})

// Store actions
export const appActions = {
  setCurrentConversation(conversationId?: string) {
    appStore.currentConversationId = conversationId
    // Clear chat when switching conversations
    if (conversationId !== appStore.currentConversationId) {
      chatActions.clearMessages()
    }
  },

  setCurrentModel(modelName?: string) {
    appStore.currentModelName = modelName
    appStore.settings.model = modelName || appStore.settings.model
  },

  toggleSidebar() {
    appStore.sidebar.isCollapsed = !appStore.sidebar.isCollapsed
  },

  setSidebarSection(section: SidebarState['activeSection']) {
    appStore.sidebar.activeSection = section
  },

  openSearch() {
    appStore.search.isOpen = true
  },

  closeSearch() {
    appStore.search.isOpen = false
    appStore.search.query = ''
    appStore.search.results = []
  },

  setSearchQuery(query: string) {
    appStore.search.query = query
  },

  setSearchResults(results: SearchResult[]) {
    appStore.search.results = results
    appStore.search.isSearching = false
  },

  setSearching(isSearching: boolean) {
    appStore.search.isSearching = isSearching
  },

  updateSettings(updates: Partial<SettingsState>) {
    Object.assign(appStore.settings, updates)
  },

  setGlobalError(error?: string) {
    appStore.globalError = error
  },

  setAppLoading(isLoading: boolean) {
    appStore.isAppLoading = isLoading
  },

  setInitialized(isInitialized: boolean) {
    appStore.isInitialized = isInitialized
  },

  setTheme(theme: 'dark' | 'light') {
    appStore.theme = theme
    appStore.settings.theme = theme
  },
}

export const chatActions = {
  addMessage(message: Message) {
    chatStore.messages.push(message)
  },

  updateLastMessage(content: string) {
    const lastMessage = chatStore.messages[chatStore.messages.length - 1]
    if (lastMessage && lastMessage.role === 'assistant') {
      lastMessage.content = content
    }
  },

  appendToResponse(token: string) {
    chatStore.currentResponse += token
    // Update the last assistant message
    const lastMessage = chatStore.messages[chatStore.messages.length - 1]
    if (lastMessage && lastMessage.role === 'assistant') {
      lastMessage.content = chatStore.currentResponse
    }
  },

  setStreaming(isStreaming: boolean) {
    chatStore.isStreaming = isStreaming
    if (!isStreaming) {
      chatStore.currentResponse = ''
    }
  },

  setLoading(isLoading: boolean) {
    chatStore.isLoading = isLoading
  },

  setError(error?: string) {
    chatStore.error = error
  },

  setInputValue(value: string) {
    chatStore.inputValue = value
  },

  setComposing(isComposing: boolean) {
    chatStore.isComposing = isComposing
  },

  clearMessages() {
    chatStore.messages = []
    chatStore.currentResponse = ''
    chatStore.isStreaming = false
    chatStore.error = undefined
  },

  setMessages(messages: Message[]) {
    chatStore.messages = messages
  },

  selectMessage(messageId: string) {
    chatStore.selectedMessages.add(messageId)
  },

  deselectMessage(messageId: string) {
    chatStore.selectedMessages.delete(messageId)
  },

  clearSelection() {
    chatStore.selectedMessages.clear()
  },

  setEditingMessage(messageId?: string) {
    chatStore.editingMessageId = messageId
  },
}

export const documentActions = {
  addToUploadQueue(files: File[]) {
    documentStore.uploadQueue.push(...files)
  },

  removeFromUploadQueue(index: number) {
    documentStore.uploadQueue.splice(index, 1)
  },

  clearUploadQueue() {
    documentStore.uploadQueue = []
  },

  setUploadProgress(filename: string, progress: number) {
    documentStore.uploadProgress[filename] = progress
  },

  clearUploadProgress(filename: string) {
    delete documentStore.uploadProgress[filename]
  },

  setUploading(isUploading: boolean) {
    documentStore.isUploading = isUploading
  },

  addProcessingDocument(documentId: string) {
    documentStore.processingDocuments.add(documentId)
  },

  removeProcessingDocument(documentId: string) {
    documentStore.processingDocuments.delete(documentId)
  },

  setLastUploadedDocument(document: Document) {
    documentStore.lastUploadedDocument = document
  },
}

// Custom hooks for using stores
export const useAppStore = () => useSnapshot(appStore)
export const useChatStore = () => useSnapshot(chatStore)
export const useDocumentStore = () => useSnapshot(documentStore)

// Persist settings to localStorage
subscribeKey(appStore.settings, 'model', (model) => {
  localStorage.setItem('locali-settings-model', model)
})

subscribeKey(appStore.settings, 'theme', (theme) => {
  localStorage.setItem('locali-settings-theme', theme)
  document.documentElement.classList.toggle('dark', theme === 'dark')
})

subscribeKey(appStore.settings, 'temperature', (temperature) => {
  localStorage.setItem('locali-settings-temperature', temperature.toString())
})

subscribeKey(appStore.settings, 'maxTokens', (maxTokens) => {
  localStorage.setItem('locali-settings-maxTokens', maxTokens.toString())
})

// Load settings from localStorage on init
export const loadPersistedSettings = () => {
  const model = localStorage.getItem('locali-settings-model')
  const theme = localStorage.getItem('locali-settings-theme') as 'dark' | 'light'
  const temperature = localStorage.getItem('locali-settings-temperature')
  const maxTokens = localStorage.getItem('locali-settings-maxTokens')

  if (model) appStore.settings.model = model
  if (theme) appStore.settings.theme = theme
  if (temperature) appStore.settings.temperature = parseFloat(temperature)
  if (maxTokens) appStore.settings.maxTokens = parseInt(maxTokens)

  // Apply theme
  if (theme) {
    appStore.theme = theme
    document.documentElement.classList.toggle('dark', theme === 'dark')
  }
}

// frontend/src/lib/queries.ts

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from './api'
import { appActions, chatActions, documentActions } from '@/store'
import type {
  Conversation,
  ConversationDetail,
  Model,
  Document,
  SearchRequest,
  SendMessageRequest,
  CreateConversationRequest,
  UpdateConversationRequest,
} from '@/types'

// Query keys
export const queryKeys = {
  conversations: ['conversations'] as const,
  conversation: (id: string) => ['conversation', id] as const,
  models: ['models'] as const,
  systemStatus: ['system', 'status'] as const,
  documents: ['documents'] as const,
  document: (id: string) => ['document', id] as const,
  searchStats: ['search', 'stats'] as const,
  tasks: ['tasks'] as const,
  systemHealth: ['system', 'health'] as const,
}

// Conversation queries
export const useConversations = () => {
  return useQuery({
    queryKey: queryKeys.conversations,
    queryFn: () => api.getConversations(),
    staleTime: 1000 * 60 * 5, // 5 minutes
  })
}

export const useConversation = (id: string | undefined) => {
  return useQuery({
    queryKey: queryKeys.conversation(id!),
    queryFn: () => api.getConversation(id!),
    enabled: !!id,
    staleTime: 1000 * 60, // 1 minute
  })
}

// Model queries
export const useModels = () => {
  return useQuery({
    queryKey: queryKeys.models,
    queryFn: () => api.getModels(),
    staleTime: 1000 * 60 * 10, // 10 minutes
  })
}

export const useSystemStatus = () => {
  return useQuery({
    queryKey: queryKeys.systemStatus,
    queryFn: () => api.getSystemStatus(),
    refetchInterval: 1000 * 30, // 30 seconds
  })
}

// Document queries
export const useDocuments = () => {
  return useQuery({
    queryKey: queryKeys.documents,
    queryFn: () => api.getDocuments(),
    staleTime: 1000 * 60 * 5, // 5 minutes
  })
}

export const useDocument = (id: string | undefined) => {
  return useQuery({
    queryKey: queryKeys.document(id!),
    queryFn: () => api.getDocument(id!),
    enabled: !!id,
  })
}

// Search queries
export const useSearchStats = () => {
  return useQuery({
    queryKey: queryKeys.searchStats,
    queryFn: () => api.getSearchStats(),
    staleTime: 1000 * 60 * 5, // 5 minutes
  })
}

// System health query
export const useSystemHealth = () => {
  return useQuery({
    queryKey: queryKeys.systemHealth,
    queryFn: () => api.getSystemHealth(),
    refetchInterval: 1000 * 60, // 1 minute
  })
}

// Mutations
export const useCreateConversation = () => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: CreateConversationRequest) => api.createConversation(data),
    onSuccess: (newConversation) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.conversations })
      appActions.setCurrentConversation(newConversation.id)
    },
  })
}

export const useUpdateConversation = () => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateConversationRequest }) =>
      api.updateConversation(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.conversations })
      queryClient.invalidateQueries({ queryKey: queryKeys.conversation(id) })
    },
  })
}

export const useDeleteConversation = () => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: string) => api.deleteConversation(id),
    onSuccess: (_, deletedId) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.conversations })
      // If deleted conversation was current, clear it
      if (appActions) {
        appActions.setCurrentConversation(undefined)
      }
    },
  })
}

export const useSendMessage = () => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({
      conversationId,
      data
    }: {
      conversationId: string
      data: SendMessageRequest
    }) => {
      chatActions.setStreaming(true)
      chatActions.setError(undefined)

      // Add user message immediately
      const userMessage = {
        id: crypto.randomUUID(),
        role: 'user' as const,
        content: data.message,
        timestamp: new Date().toISOString(),
      }
      chatActions.addMessage(userMessage)

      // Add placeholder assistant message
      const assistantMessage = {
        id: crypto.randomUUID(),
        role: 'assistant' as const,
        content: '',
        timestamp: new Date().toISOString(),
      }
      chatActions.addMessage(assistantMessage)

      try {
        const stream = await api.sendMessage(conversationId, data)
        const reader = stream.getReader()

        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          chatActions.appendToResponse(value)
        }

        chatActions.setStreaming(false)

        // Invalidate conversation data
        queryClient.invalidateQueries({
          queryKey: queryKeys.conversation(conversationId)
        })
        queryClient.invalidateQueries({
          queryKey: queryKeys.conversations
        })

      } catch (error) {
        chatActions.setStreaming(false)
        chatActions.setError(error instanceof Error ? error.message : 'Failed to send message')
        throw error
      }
    },
  })
}

export const useLoadModel = () => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (modelName: string) => api.loadModel(modelName),
    onSuccess: (_, modelName) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.models })
      queryClient.invalidateQueries({ queryKey: queryKeys.systemStatus })
      appActions.setCurrentModel(modelName)
    },
  })
}

export const useSwitchModel = () => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (modelName: string) => api.switchModel(modelName),
    onSuccess: (_, modelName) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.models })
      queryClient.invalidateQueries({ queryKey: queryKeys.systemStatus })
      appActions.setCurrentModel(modelName)
    },
  })
}

export const useUploadDocument = () => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (file: File) => {
      documentActions.setUploading(true)
      return api.uploadDocument(file)
    },
    onSuccess: (document) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.documents })
      queryClient.invalidateQueries({ queryKey: queryKeys.searchStats })
      documentActions.setLastUploadedDocument(document)
      documentActions.setUploading(false)
    },
    onError: () => {
      documentActions.setUploading(false)
    },
  })
}

export const useDeleteDocument = () => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: string) => api.deleteDocument(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.documents })
      queryClient.invalidateQueries({ queryKey: queryKeys.searchStats })
    },
  })
}

export const useSearch = () => {
  return useMutation({
    mutationFn: (data: SearchRequest) => {
      appActions.setSearching(true)
      return api.search(data)
    },
    onSuccess: (response) => {
      appActions.setSearchResults(response.results)
      appActions.setSearching(false)
    },
    onError: () => {
      appActions.setSearching(false)
    },
  })
}