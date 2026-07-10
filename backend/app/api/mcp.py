from fastapi import APIRouter, Depends

from ..api.deps import get_current_user
from ..api.schemas import SearchRequest, SearchResponse, SummarizationRequest, SummarizationResponse
from ..database.database import get_db
from ..database import models
from ..services.chat_service import ChatService
from sqlalchemy.orm import Session

router = APIRouter(prefix="/mcp", tags=["mcp"])


@router.post("/search", response_model=SearchResponse)
async def search_documents(
    request: SearchRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = ChatService(db)
    chunks = service.retrieve_relevant_chunks(request.query, user_id=current_user.id, limit=8)
    return SearchResponse(chunks=[chunk.text for chunk in chunks])


@router.post("/summarize", response_model=SummarizationResponse)
async def summarize_text(
    request: SummarizationRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = ChatService(db)
    summary = service.summarize_text(request.text)
    return SummarizationResponse(summary=summary)
