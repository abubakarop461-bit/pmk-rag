from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from typing import List, Optional
from loguru import logger

from app.core.security import get_current_user
from app.core.supabase import get_supabase_client
from app.core.qdrant import get_qdrant_client
from app.repositories.chat_repository import ChatRepository
from app.repositories.vector_repository import VectorRepository
from app.services.embedding_service import EmbeddingService
from app.services.retrieval_service import RetrievalService
from app.services.conversation_service import ConversationService
from app.services.memory_service import MemoryService
from app.services.prompt_builder_service import PromptBuilderService
from app.services.answer_validation_service import AnswerValidationService
from app.services.chat_analytics_service import ChatAnalyticsService
from app.services.chat_service import ChatService
from app.schemas.chat import ChatSessionCreateRequest, ChatSessionResponse, ChatQueryRequest, ChatMessageResponse

router = APIRouter(prefix="/chat", tags=["chat"])

def get_chat_service() -> ChatService:
    db = get_supabase_client()
    qdrant = get_qdrant_client()
    chat_repo = ChatRepository(db)
    v_repo = VectorRepository(qdrant)
    
    embed = EmbeddingService()
    retrieval = RetrievalService(v_repo, embed)
    conversation = ConversationService(chat_repo)
    memory = MemoryService(chat_repo)
    prompt = PromptBuilderService()
    validation = AnswerValidationService()
    analytics = ChatAnalyticsService(chat_repository=chat_repo)
    
    return ChatService(
        retrieval_service=retrieval,
        conversation_service=conversation,
        memory_service=memory,
        prompt_builder=prompt,
        validation_service=validation,
        analytics_service=analytics
    )

def get_conversation_service() -> ConversationService:
    db = get_supabase_client()
    chat_repo = ChatRepository(db)
    return ConversationService(chat_repo)

@router.post("/session", response_model=ChatSessionResponse)
async def create_session(
    request_in: ChatSessionCreateRequest,
    conv_svc: ConversationService = Depends(get_conversation_service),
    current_user: dict = Depends(get_current_user)
):
    """
    Creates a new conversation session mapped to a specific project.
    """
    try:
        user_id = current_user.get("id")
        session = conv_svc.create_chat_session(
            project_id=request_in.project_id,
            title=request_in.title,
            user_id=user_id
        )
        return session
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create chat session: {e}"
        )

@router.get("/sessions", response_model=List[ChatSessionResponse])
async def list_sessions(
    project_id: str,
    conv_svc: ConversationService = Depends(get_conversation_service),
    current_user: dict = Depends(get_current_user)
):
    """
    Lists all chat sessions belonging to a project for the authenticated user.
    """
    user_id = current_user.get("id")
    sessions = conv_svc.list_sessions_for_project(project_id=project_id, user_id=user_id)
    return sessions

@router.delete("/session/{session_id}")
async def delete_session(
    session_id: str,
    conv_svc: ConversationService = Depends(get_conversation_service),
    current_user: dict = Depends(get_current_user)
):
    """
    Deletes a conversation session thread.
    """
    success = conv_svc.delete_chat_session(session_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found or deletion failed."
        )
    return {"message": "Session deleted successfully"}

@router.get("/session/{session_id}/history", response_model=List[ChatMessageResponse])
async def get_session_history(
    session_id: str,
    conv_svc: ConversationService = Depends(get_conversation_service),
    current_user: dict = Depends(get_current_user)
):
    """
    Retrieves chronological conversation history messages for a session.
    """
    messages = conv_svc.get_chat_history(session_id)
    return messages

@router.patch("/session/{session_id}/title", response_model=ChatSessionResponse)
async def rename_session(
    session_id: str,
    title: str,
    conv_svc: ConversationService = Depends(get_conversation_service),
    current_user: dict = Depends(get_current_user)
):
    """
    Renames an existing chat session thread.
    """
    try:
        session = conv_svc.rename_chat_session(session_id, title)
        return session
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to rename session: {e}"
        )

@router.post("/stream")
async def chat_stream(
    request_in: ChatQueryRequest,
    chat_svc: ChatService = Depends(get_chat_service),
    current_user: dict = Depends(get_current_user)
):
    """
    SSE stream endpoint yielding RAG response tokens and final metadata.
    """
    async def event_generator():
        try:
            async for chunk in chat_svc.stream_chat(
                query=request_in.query,
                session_id=request_in.session_id,
                project_id=request_in.project_id,
                max_tokens=request_in.max_tokens
            ):
                yield f"data: {chunk}\n\n"
        except Exception as e:
            logger.error(f"Event generator crash: {e}")
            yield f"data: {{\"error\": \"Streaming aborted due to internal server error\"}}\n\n"
        yield "data: [DONE]\n\n"
        
    return StreamingResponse(event_generator(), media_type="text/event-stream")
