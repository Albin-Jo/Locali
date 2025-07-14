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