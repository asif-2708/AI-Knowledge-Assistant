from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..api.deps import get_current_user
from ..api.schemas import ChatRequest, ChatResponse
from ..database.database import get_db
from ..database import models
from ..services.chat_service import ChatService

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/query", response_model=ChatResponse)
async def query_chat(
    request: ChatRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = ChatService(db)
    answer = await service.answer_question(user_id=current_user.id, question=request.question)
    return ChatResponse(answer=answer)


@router.get("/stream")
async def stream_chat(
    question: str = Query(...),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = ChatService(db)
    generator = service.stream_answer(user_id=current_user.id, question=question)
    return StreamingResponse(generator, media_type="text/event-stream")
