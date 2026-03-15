import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api.routes import query, compare, contradictions, verse, debate, topics
from app.core.config import get_settings
from app.core.qdrant_client import ensure_collection_exists

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()

# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------
limiter = Limiter(key_func=get_remote_address, default_limits=[settings.rate_limit])


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("CrossVerse API starting up...")
    await ensure_collection_exists()
    yield
    logger.info("CrossVerse API shutting down.")


app = FastAPI(
    title="CrossVerse API",
    description=(
        "AI-powered platform for exploring religious texts across traditions. "
        "Uses RAG (Retrieval Augmented Generation) to answer questions grounded "
        "exclusively in scripture."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ---------------------------------------------------------------------------
# CORS — driven by ALLOWED_ORIGINS env var
# ---------------------------------------------------------------------------
allowed_origins = [o.strip() for o in settings.allowed_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(query.router, tags=["Query"])
app.include_router(compare.router, tags=["Compare"])
app.include_router(contradictions.router, tags=["Contradictions"])
app.include_router(verse.router, tags=["Verse"])
app.include_router(debate.router, tags=["Debate"])
app.include_router(topics.router, tags=["Topics"])


@app.get("/", tags=["Health"])
async def root():
    return {
        "name": "CrossVerse",
        "description": "Cross-religious scripture exploration engine",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok"}
