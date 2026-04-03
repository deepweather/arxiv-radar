from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://arxiv_radar:changeme_in_production@postgres:5432/arxiv_radar"

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # Auth
    secret_key: str = "changeme_generate_with_python_secrets_token_urlsafe_32"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # ArXiv
    arxiv_categories: str = "cs.CV,cs.LG,cs.CL,cs.AI,cs.NE,cs.RO"
    arxiv_ingest_interval_minutes: int = 30
    arxiv_ingest_batch_size: int = 2000

    # Embedding
    embedding_model: str = "all-MiniLM-L6-v2"
    model_cache_dir: str = "/app/model_cache"

    # Email
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    email_from: str = "noreply@arxiv-radar.local"

    # Semantic Scholar
    semantic_scholar_api_key: str = ""

    # Security
    cookie_secure: bool = False

    # CORS
    cors_origins: str = "http://localhost:5173,http://localhost:8080"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
