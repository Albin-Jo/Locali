// frontend/README.md

# Locali Frontend

Modern React frontend for the Locali AI coding assistant.

## Features

- 🎨 **Modern UI** - Clean, dark theme with Tailwind CSS
- ⚡ **Real-time Chat** - Streaming responses with Server-Sent Events
- 📁 **Document Management** - Upload, process, and search through files
- 🔍 **Hybrid Search** - Vector similarity + keyword search
- 🎛️ **Model Management** - Switch between different AI models
- 📱 **Responsive** - Works on desktop and mobile
- ⌨️ **Keyboard Shortcuts** - Fast navigation and actions
- 🔐 **Privacy-First** - All processing happens locally

## Tech Stack

- **React 18** - Modern React with hooks and concurrent features
- **TypeScript** - Type-safe development
- **Tailwind CSS** - Utility-first CSS framework
- **Valtio** - Proxy-based state management
- **TanStack Query** - Server state management
- **Vite** - Fast build tool and dev server
- **Monaco Editor** - VS Code editor for code display

## Getting Started

### Prerequisites

- Node.js 18+ 
- npm or yarn
- Backend server running on localhost:8080

### Installation

1. Install dependencies:
```bash
npm install
```

2. Start development server:
```bash
npm run dev
```

3. Open [http://localhost:3000](http://localhost:3000)

### Build for Production

```bash
npm run build
```

The built files will be in the `dist` directory.

## Project Structure

```
src/
├── components/          # Reusable UI components
│   ├── ui/             # Basic UI components (Button, Input, etc.)
│   ├── chat/           # Chat-related components
│   ├── documents/      # Document management components
│   ├── models/         # Model selection components
│   └── layout/         # Layout components
├── pages/              # Main application pages
├── hooks/              # Custom React hooks
├── lib/                # Utilities and API client
├── store/              # State management
├── types/              # TypeScript type definitions
└── styles/             # Global styles and themes
```

## Key Components

### Chat Interface
- `MessageList` - Displays conversation messages
- `ChatInput` - Message input with file upload
- `Message` - Individual message with code highlighting
- `CodeBlock` - Syntax-highlighted code display

### Document Management
- `DocumentList` - Browse uploaded documents
- `DocumentUpload` - File upload with drag & drop
- `DocumentItem` - Individual document display

### Search
- `SearchOverlay` - Global search interface
- `SearchResults` - Display search results

### Settings
- `ModelSelector` - Choose AI models
- `SettingsPage` - Configure application settings

## Keyboard Shortcuts

- `Cmd/Ctrl + K` - Open search
- `Cmd/Ctrl + N` - New conversation
- `Cmd/Ctrl + ,` - Open settings
- `Escape` - Close modals/overlays
- `Enter` - Send message
- `Shift + Enter` - New line in message

## API Integration

The frontend communicates with the backend through:

- **REST API** - Standard CRUD operations
- **Server-Sent Events** - Real-time streaming responses
- **File Upload** - Multipart form data for documents

See `src/lib/api.ts` for the complete API client.

## State Management

Uses Valtio for reactive state management:

- `appStore` - Global application state
- `chatStore` - Chat-specific state  
- `documentStore` - Document upload state

TanStack Query handles server state caching and synchronization.

## Styling

- **Tailwind CSS** - Utility classes for styling
- **CSS Variables** - Dynamic theming support
- **Custom Components** - Consistent design system
- **Dark Theme** - Primary theme with light theme support

## Development

### Code Style

- TypeScript strict mode enabled
- ESLint with React rules
- Prettier for code formatting
- Absolute imports with `@/` alias

### Performance

- Code splitting with dynamic imports
- Image optimization with proper formats
- Bundle analysis with `npm run build`
- React Query for request caching

## Contributing

1. Follow TypeScript best practices
2. Add proper error handling
3. Include loading states for async operations
4. Test on different screen sizes
5. Maintain accessibility standards

## License

MIT License - see LICENSE file for details