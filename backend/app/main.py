from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.config import settings
from .database.database import Base, engine
from .api import auth, upload, chat, document, mcp

from sqlalchemy.exc import OperationalError

app = FastAPI(title=settings.project_name, debug=settings.debug)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event() -> None:
    try:
        Base.metadata.create_all(bind=engine)
    except OperationalError as exc:
        app.logger = app.logger if hasattr(app, 'logger') else None
        print("WARNING: Could not initialize database:", exc)
        print("Please verify your DATABASE_URL in backend/.env is correct and PostgreSQL is running.")

app.include_router(auth.router)
app.include_router(upload.router)
app.include_router(chat.router)
app.include_router(document.router)
app.include_router(mcp.router)


@app.get("/")
async def read_root():
    return {"message": "AI Knowledge Assistant backend is running."}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=settings.debug)
