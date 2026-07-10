from fastapi import APIRouter

router = APIRouter(prefix="/mcp", tags=["mcp"])


@router.get("/health")
def health():
    return {"status": "ok"}
