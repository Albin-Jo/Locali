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