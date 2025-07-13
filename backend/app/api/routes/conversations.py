from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from loguru import logger
from pydantic import BaseModel, Field

from ...services.conversation_manager import ConversationManager


# Dependency placeholders - will be overridden in main.py
async def get_model_manager():
    raise NotImplementedError


async def get_conversation_manager():
    raise NotImplementedError


# Request/Response Models
class CreateConversationRequest(BaseModel):
    title: Optional[str] = None
    model_name: Optional[str] = None


class SendMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=10000)
    model_name: Optional[str] = None
    stream: bool = True
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, ge=1, le=4096)


class UpdateConversationRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)


class ConversationResponse(BaseModel):
    id: str
    title: Optional[str]
    message_count: int
    model_name: Optional[str]
    created_at: str
    updated_at: str


class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    timestamp: str
    tokens: Optional[int] = None


class ConversationDetailResponse(BaseModel):
    id: str
    title: Optional[str]
    messages: List[MessageResponse]
    model_name: Optional[str]
    created_at: str
    updated_at: str


# Router
router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.post("/", response_model=ConversationResponse)
async def create_conversation(
        request: CreateConversationRequest,
        conversation_manager: ConversationManager = Depends(get_conversation_manager)
):
    """Create a new conversation."""
    try:
        conversation = await conversation_manager.create_conversation(
            title=request.title,
            model_name=request.model_name
        )

        return ConversationResponse(
            id=conversation.id,
            title=conversation.title,
            message_count=len(conversation.messages),
            model_name=conversation.model_name,
            created_at=conversation.created_at.isoformat(),
            updated_at=conversation.updated_at.isoformat()
        )

    except Exception as e:
        logger.error(f"Failed to create conversation: {e}")
        raise HTTPException(status_code=500, detail="Failed to create conversation")


@router.get("/", response_model=List[ConversationResponse])
async def list_conversations(
        conversation_manager: ConversationManager = Depends(get_conversation_manager)
):
    """List all conversations."""
    try:
        conversations = await conversation_manager.list_conversations()

        return [
            ConversationResponse(
                id=conv['id'],
                title=conv['title'],
                message_count=conv['message_count'],
                model_name=conv['model_name'],
                created_at=conv['created_at'],
                updated_at=conv['updated_at']
            )
            for conv in conversations
        ]

    except Exception as e:
        logger.error(f"Failed to list conversations: {e}")
        raise HTTPException(status_code=500, detail="Failed to list conversations")


@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
        conversation_id: str,
        conversation_manager: ConversationManager = Depends(get_conversation_manager)
):
    """Get a specific conversation with all messages."""
    try:
        conversation = await conversation_manager.get_conversation(conversation_id)

        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        messages = [
            MessageResponse(
                id=msg.id,
                role=msg.role,
                content=msg.content,
                timestamp=msg.timestamp.isoformat(),
                tokens=msg.tokens
            )
            for msg in conversation.messages
        ]

        return ConversationDetailResponse(
            id=conversation.id,
            title=conversation.title,
            messages=messages,
            model_name=conversation.model_name,
            created_at=conversation.created_at.isoformat(),
            updated_at=conversation.updated_at.isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get conversation {conversation_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get conversation")


@router.post("/{conversation_id}/messages")
async def send_message(
        conversation_id: str,
        request: SendMessageRequest,
        conversation_manager: ConversationManager = Depends(get_conversation_manager)
):
    """Send a message to a conversation and get AI response."""
    try:
        # Validate conversation exists or will be created
        conversation = await conversation_manager.get_conversation(conversation_id)

        if request.stream:
            # Streaming response
            async def generate():
                try:
                    async for token in conversation_manager.generate_response(
                            conversation_id=conversation_id,
                            user_message=request.message,
                            model_name=request.model_name,
                            stream=True,
                            temperature=request.temperature,
                            max_tokens=request.max_tokens
                    ):
                        # Server-Sent Events format
                        yield f"data: {token}\n\n"

                    # End of stream marker
                    yield "data: [DONE]\n\n"

                except Exception as e:
                    logger.error(f"Streaming error: {e}")
                    yield f"data: Error: {str(e)}\n\n"
                    yield "data: [DONE]\n\n"

            return StreamingResponse(
                generate(),
                media_type="text/plain",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "Content-Type": "text/plain; charset=utf-8"
                }
            )

        else:
            # Non-streaming response
            response_content = ""
            async for token in conversation_manager.generate_response(
                    conversation_id=conversation_id,
                    user_message=request.message,
                    model_name=request.model_name,
                    stream=False,
                    temperature=request.temperature,
                    max_tokens=request.max_tokens
            ):
                response_content = token  # Non-streaming returns full response
                break

            return {"response": response_content}

    except Exception as e:
        logger.error(f"Failed to send message: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send message: {str(e)}")


@router.put("/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
        conversation_id: str,
        request: UpdateConversationRequest,
        conversation_manager: ConversationManager = Depends(get_conversation_manager)
):
    """Update conversation title."""
    try:
        success = await conversation_manager.update_conversation_title(
            conversation_id, request.title
        )

        if not success:
            raise HTTPException(status_code=404, detail="Conversation not found")

        # Return updated conversation
        conversation = await conversation_manager.get_conversation(conversation_id)
        return ConversationResponse(
            id=conversation.id,
            title=conversation.title,
            message_count=len(conversation.messages),
            model_name=conversation.model_name,
            created_at=conversation.created_at.isoformat(),
            updated_at=conversation.updated_at.isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update conversation {conversation_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update conversation")


@router.delete("/{conversation_id}")
async def delete_conversation(
        conversation_id: str,
        conversation_manager: ConversationManager = Depends(get_conversation_manager)
):
    """Delete a conversation."""
    try:
        success = await conversation_manager.delete_conversation(conversation_id)

        if not success:
            raise HTTPException(status_code=404, detail="Conversation not found")

        return {"message": "Conversation deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete conversation {conversation_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete conversation")


@router.get("/{conversation_id}/context")
async def get_conversation_context(
        conversation_id: str,
        conversation_manager: ConversationManager = Depends(get_conversation_manager)
):
    """Get conversation context information."""
    try:
        context = await conversation_manager.get_conversation_context(conversation_id)

        if not context:
            raise HTTPException(status_code=404, detail="Conversation not found")

        return context

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get conversation context {conversation_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get conversation context")
