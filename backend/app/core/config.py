import socket
from pydantic_settings import BaseSettings, SettingsConfigDict


def get_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    project_name: str = "AI Knowledge Assistant"
    debug: bool = True
    secret_key: str = "change-this-secret-key"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    database_url: str = "postgresql://postgres:abc%40123@localhost:5432/ai_knowledge"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"
    # Use local sentence-transformers model for embeddings instead of external API
    use_local_embeddings: bool = True
    local_embedding_model: str = "all-MiniLM-L6-v2"
    frontend_url: str = "http://localhost:4200"
    cors_origins: list[str] = [
        "http://localhost:4200",
        "http://127.0.0.1:4200",
        f"http://{get_local_ip()}:4200"
    ]


settings = Settings()

# Generate a new random secret key on every server startup to invalidate tokens on restart
import secrets
settings.secret_key = secrets.token_hex(32)
