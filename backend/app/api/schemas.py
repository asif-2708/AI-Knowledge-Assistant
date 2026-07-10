from datetime import datetime
from typing import List

from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str


class DocumentResponse(BaseModel):
    id: int
    filename: str
    uploaded_at: datetime

    class Config:
        from_attributes = True


class ChatRequest(BaseModel):
    question: str


class ChatResponse(BaseModel):
    answer: str


class SearchRequest(BaseModel):
    query: str


class SearchResponse(BaseModel):
    chunks: List[str]


class SummarizationRequest(BaseModel):
    text: str


class SummarizationResponse(BaseModel):
    summary: str
