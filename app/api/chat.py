from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.ai.gemini_client import GeminiError
from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.chat import ChatRequest, ChatResponse, ChatSessionMessages, ChatSessionOut
from app.services import chat_service

router = APIRouter(prefix="/chat", tags=["AI Chat"])


@router.post("", response_model=ChatResponse)
def send_chat_message(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return chat_service.send_message(db, current_user, payload.session_id, payload.message)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except GeminiError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"AI assistant unavailable: {exc}",
        )


@router.get("/sessions", response_model=List[ChatSessionOut])
def list_chat_sessions(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    return chat_service.list_sessions(db, current_user)


@router.get("/sessions/{session_id}/messages", response_model=ChatSessionMessages)
def get_chat_session_messages(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        messages = chat_service.get_session_messages(db, current_user, session_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return {"session_id": session_id, "messages": messages}
