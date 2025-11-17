import json
import os
import tempfile
import uuid
from collections import OrderedDict
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, AsyncIterator, Any

from loguru import logger

from .model_manager import ModelManager
from ..core.config import settings
from ..core.logging import log_performance
from ..utils.token_counter import get_token_counter


@dataclass
class Message:
    """Represents a single message in a conversation."""
    id: str
    role: str  # 'user', 'assistant', 'system'
    content: str
    timestamp: datetime
    tokens: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> dict:
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict) -> 'Message':
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


@dataclass
class Conversation:
    """Represents a conversation with message history."""
    id: str
    title: Optional[str]
    messages: List[Message]
    created_at: datetime
    updated_at: datetime
    model_name: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> dict:
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        data['updated_at'] = self.updated_at.isoformat()
        data['messages'] = [msg.to_dict() for msg in self.messages]
        return data

    @classmethod
    def from_dict(cls, data: dict) -> 'Conversation':
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        data['messages'] = [Message.from_dict(msg) for msg in data['messages']]
        return cls(**data)


class ConversationStorage:
    """Handles persistent storage of conversations."""

    def __init__(self, storage_path: str):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.conversations_file = self.storage_path / "conversations.json"
        self._ensure_storage_file()

    def _ensure_storage_file(self):
        """Ensure the conversations file exists."""
        if not self.conversations_file.exists():
            self.conversations_file.write_text(json.dumps({}))

    def _atomic_write(self, data: dict):
        """Atomically write data to file using temp file + rename.

        This prevents corruption from concurrent writes or crashes mid-write.
        The rename operation is atomic on POSIX systems.
        """
        # Create temp file in same directory (same filesystem for atomic rename)
        fd, temp_path = tempfile.mkstemp(
            dir=self.storage_path,
            prefix='.conversations_',
            suffix='.tmp'
        )

        try:
            # Write data to temp file
            with os.fdopen(fd, 'w') as f:
                json.dump(data, f, indent=2)

            # Atomic rename (replaces old file)
            os.replace(temp_path, self.conversations_file)

        except Exception as e:
            # Clean up temp file on error
            try:
                os.unlink(temp_path)
            except:
                pass
            raise e

    async def save_conversation(self, conversation: Conversation):
        """Save a conversation to storage."""
        conversations = await self.load_all_conversations()
        conversations[conversation.id] = conversation.to_dict()

        # Atomic write to prevent corruption
        self._atomic_write(conversations)

    async def load_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Load a specific conversation."""
        conversations = await self.load_all_conversations()
        if conversation_id in conversations:
            return Conversation.from_dict(conversations[conversation_id])
        return None

    async def load_all_conversations(self) -> Dict[str, dict]:
        """Load all conversations metadata."""
        try:
            with open(self.conversations_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    async def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation."""
        conversations = await self.load_all_conversations()
        if conversation_id in conversations:
            del conversations[conversation_id]
            # Atomic write to prevent corruption
            self._atomic_write(conversations)
            return True
        return False

    async def list_conversations(self) -> List[Dict[str, Any]]:
        """List all conversations with basic info."""
        conversations = await self.load_all_conversations()

        conversation_list = []
        for conv_id, conv_data in conversations.items():
            conversation_list.append({
                'id': conv_id,
                'title': conv_data.get('title'),
                'created_at': conv_data.get('created_at'),
                'updated_at': conv_data.get('updated_at'),
                'message_count': len(conv_data.get('messages', [])),
                'model_name': conv_data.get('model_name')
            })

        # Sort by updated_at descending
        conversation_list.sort(
            key=lambda x: x['updated_at'] or x['created_at'],
            reverse=True
        )

        return conversation_list


class ContextManager:
    """Manages conversation context within model limits."""

    def __init__(self, max_context_length: int = 8192):
        self.max_context_length = max_context_length
        self.system_prompt = self._get_system_prompt()
        self.token_counter = get_token_counter()

    def _get_system_prompt(self) -> str:
        """Get the system prompt for the coding assistant."""
        return """You are CodeAssist AI, a helpful programming assistant that provides accurate, concise, and practical coding help.

Key guidelines:
- Provide working code examples with clear explanations
- Focus on best practices and modern conventions
- Explain complex concepts in simple terms
- Always test your code suggestions mentally before responding
- When debugging, ask clarifying questions if the problem isn't clear
- Prefer readable, maintainable code over clever one-liners
- Include error handling where appropriate

You can help with:
- Code writing and debugging
- Algorithm explanations
- Code reviews and improvements
- Architecture suggestions
- Performance optimization
- Documentation and comments

Respond in a conversational tone while being technically accurate."""

    def prepare_prompt(self, messages: List[Message], model_name: str = None) -> str:
        """Prepare prompt from conversation messages with context management."""

        # Start with system prompt
        prompt_parts = [f"System: {self.system_prompt}\n"]

        # Count tokens accurately using tiktoken
        current_tokens = self.token_counter.count_tokens(self.system_prompt)
        max_tokens = self.max_context_length - 1000  # Reserve space for response

        # Add messages in reverse order (most recent first)
        included_messages = []
        for message in reversed(messages):
            # Accurate token count for message
            message_tokens = self.token_counter.count_tokens(
                f"{message.role.capitalize()}: {message.content}"
            )

            if current_tokens + message_tokens > max_tokens:
                break

            included_messages.insert(0, message)
            current_tokens += message_tokens

        # Format messages
        for message in included_messages:
            role = message.role.capitalize()
            prompt_parts.append(f"{role}: {message.content}\n")

        # Add assistant prompt
        prompt_parts.append("Assistant: ")

        prompt = "\n".join(prompt_parts)

        logger.debug(f"Prepared prompt with {len(included_messages)} messages, ~{current_tokens} tokens")
        return prompt

    def generate_title(self, first_message: str) -> str:
        """Generate a conversation title from the first message."""
        # Simple title generation - could be improved with AI
        words = first_message.split()[:6]  # First 6 words
        title = " ".join(words)

        # Clean up and truncate
        title = title.replace('\n', ' ').strip()
        if len(title) > 50:
            title = title[:47] + "..."

        return title or "New Conversation"


class ConversationManager:
    """Manages conversations, context, and integrates with ModelManager."""

    def __init__(self, model_manager: ModelManager, max_active_conversations: int = 100):
        self.model_manager = model_manager
        self.storage = ConversationStorage(settings.database_url.replace('.db', '_conversations'))
        self.context_manager = ContextManager(settings.max_context_length)
        self.active_conversations: OrderedDict[str, Conversation] = OrderedDict()
        self.max_active_conversations = max_active_conversations

        logger.info(f"ConversationManager initialized (max active: {max_active_conversations})")

    def _add_to_cache(self, conversation_id: str, conversation: Conversation):
        """Add conversation to cache with LRU eviction."""
        # If conversation already exists, move it to end (most recently used)
        if conversation_id in self.active_conversations:
            self.active_conversations.move_to_end(conversation_id)
        else:
            # Add new conversation
            self.active_conversations[conversation_id] = conversation

            # Evict least recently used if cache is full
            if len(self.active_conversations) > self.max_active_conversations:
                lru_id = next(iter(self.active_conversations))
                logger.debug(f"Evicting conversation {lru_id} from cache (LRU)")
                del self.active_conversations[lru_id]

    async def create_conversation(self, title: str = None, model_name: str = None) -> Conversation:
        """Create a new conversation."""
        conversation_id = str(uuid.uuid4())
        now = datetime.now()

        conversation = Conversation(
            id=conversation_id,
            title=title,
            messages=[],
            created_at=now,
            updated_at=now,
            model_name=model_name or self.model_manager.current_model
        )

        # Store in memory cache and persistence
        self._add_to_cache(conversation_id, conversation)
        await self.storage.save_conversation(conversation)

        logger.info(f"Created conversation: {conversation_id}")
        return conversation

    async def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Get a conversation by ID."""
        # Check active conversations first
        if conversation_id in self.active_conversations:
            # Mark as recently used
            self.active_conversations.move_to_end(conversation_id)
            return self.active_conversations[conversation_id]

        # Load from storage
        conversation = await self.storage.load_conversation(conversation_id)
        if conversation:
            # Add to cache with LRU eviction
            self._add_to_cache(conversation_id, conversation)

        return conversation

    async def add_message(
            self,
            conversation_id: str,
            role: str,
            content: str,
            metadata: Dict[str, Any] = None
    ) -> Message:
        """Add a message to a conversation."""
        conversation = await self.get_conversation(conversation_id)
        if not conversation:
            raise ValueError(f"Conversation {conversation_id} not found")

        # Count tokens for this message
        token_count = self.context_manager.token_counter.count_tokens(content)

        message = Message(
            id=str(uuid.uuid4()),
            role=role,
            content=content,
            timestamp=datetime.now(),
            tokens=token_count,
            metadata=metadata or {}
        )

        conversation.messages.append(message)
        conversation.updated_at = datetime.now()

        # Auto-generate title from first user message
        if not conversation.title and role == 'user' and len(conversation.messages) == 1:
            conversation.title = self.context_manager.generate_title(content)

        # Save to storage
        await self.storage.save_conversation(conversation)

        logger.debug(f"Added {role} message to conversation {conversation_id}")
        return message

    @log_performance("generate_response")
    async def generate_response(
            self,
            conversation_id: str,
            user_message: str,
            model_name: str = None,
            stream: bool = True,
            **generation_kwargs
    ) -> AsyncIterator[str]:
        """Generate AI response for a conversation."""

        # Get or create conversation
        conversation = await self.get_conversation(conversation_id)
        if not conversation:
            conversation = await self.create_conversation(model_name=model_name)
            conversation_id = conversation.id

        # Add user message
        await self.add_message(conversation_id, 'user', user_message)

        # Prepare prompt with context
        prompt = self.context_manager.prepare_prompt(
            conversation.messages,
            model_name or conversation.model_name
        )

        # Generate response
        response_content = ""
        try:
            if stream:
                async for token in self.model_manager.generate_stream(
                        prompt,
                        model_name=model_name or conversation.model_name,
                        **generation_kwargs
                ):
                    response_content += token
                    yield token
            else:
                # For non-streaming, collect all tokens
                async for token in self.model_manager.generate_stream(
                        prompt,
                        model_name=model_name or conversation.model_name,
                        **generation_kwargs
                ):
                    response_content += token
                yield response_content

        except Exception as e:
            error_message = f"Error generating response: {str(e)}"
            logger.error(error_message)
            yield error_message
            response_content = error_message

        # Add assistant response to conversation
        if response_content:
            await self.add_message(conversation_id, 'assistant', response_content.strip())

    async def list_conversations(self) -> List[Dict[str, Any]]:
        """List all conversations."""
        return await self.storage.list_conversations()

    async def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation."""
        # Remove from active conversations
        if conversation_id in self.active_conversations:
            del self.active_conversations[conversation_id]

        # Remove from storage
        return await self.storage.delete_conversation(conversation_id)

    async def update_conversation_title(self, conversation_id: str, title: str) -> bool:
        """Update conversation title."""
        conversation = await self.get_conversation(conversation_id)
        if not conversation:
            return False

        conversation.title = title
        conversation.updated_at = datetime.now()
        await self.storage.save_conversation(conversation)

        return True

    async def get_conversation_context(self, conversation_id: str) -> Dict[str, Any]:
        """Get conversation context information."""
        conversation = await self.get_conversation(conversation_id)
        if not conversation:
            return {}

        return {
            'id': conversation.id,
            'title': conversation.title,
            'message_count': len(conversation.messages),
            'model_name': conversation.model_name,
            'created_at': conversation.created_at.isoformat(),
            'updated_at': conversation.updated_at.isoformat(),
            'last_message': conversation.messages[-1].to_dict() if conversation.messages else None
        }
