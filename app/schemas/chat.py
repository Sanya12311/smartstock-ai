from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    session_id: Optional[int] = None


class ChatResponse(BaseModel):
    session_id: int
    reply: str
    disclaimer: str


class ChatMessageOut(BaseModel):
    role: str
    content: str
    created_at: datetime


class ChatSessionOut(BaseModel):
    id: int
    title: str
    created_at: datetime


class ChatSessionMessages(BaseModel):
    session_id: int
    messages: List[ChatMessageOut]
