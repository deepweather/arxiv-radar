from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db.session import engine
from app.api import auth, papers, tags, recommendations, collections, social, webhooks


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.db import models  # noqa: F401
    yield
    await engine.dispose()


app = FastAPI(
    title="arxiv-radar",
    version="0.1.0",
    description="Modern arXiv paper discovery with semantic search and personalized recommendations",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(papers.router, prefix="/api/papers", tags=["papers"])
app.include_router(tags.router, prefix="/api/tags", tags=["tags"])
app.include_router(recommendations.router, prefix="/api/recommendations", tags=["recommendations"])
app.include_router(collections.router, prefix="/api/collections", tags=["collections"])
app.include_router(social.router, prefix="/api/social", tags=["social"])
app.include_router(webhooks.router, prefix="/api/webhooks", tags=["webhooks"])


@app.get("/api/health")
async def health():
    return {"status": "ok"}
