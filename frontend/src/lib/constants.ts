// frontend/src/lib/constants.ts

export const APP_CONFIG = {
  name: 'Locali',
  version: '0.1.0',
  description: 'Privacy-first local AI coding assistant',
  github: 'https://github.com/locali/locali',
  docs: 'https://docs.locali.dev',
} as const

export const API_ENDPOINTS = {
  conversations: '/api/v1/conversations',
  models: '/api/v1/models',
  documents: '/api/v1/documents',
  search: '/api/v1/search',
  system: '/api/v1/system',
  tasks: '/api/v1/tasks',
} as const

export const KEYBOARD_SHORTCUTS = {
  search: 'cmd+k',
  newChat: 'cmd+n',
  settings: 'cmd+,',
  help: 'cmd+?',
} as const

export const THEME_COLORS = {
  primary: 'hsl(173, 100%, 42%)',
  background: 'hsl(240, 23%, 9%)',
  foreground: 'hsl(0, 0%, 100%)',
  muted: 'hsl(0, 0%, 63%)',
  border: 'hsl(240, 19%, 27%)',
  card: 'hsl(240, 19%, 16%)',
} as const

