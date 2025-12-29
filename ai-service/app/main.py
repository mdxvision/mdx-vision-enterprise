"""
MDx Vision AI Pipeline Service
Real-time transcription and clinical NLP processing
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import structlog

from app.routers import transcription, notes, translation, drugs
from app.config import settings

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    logger.info("Starting MDx AI Pipeline Service")
    yield
    logger.info("Shutting down MDx AI Pipeline Service")


app = FastAPI(
    title="MDx Vision AI Pipeline",
    description="Real-time transcription and clinical NLP processing for MDx Vision",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8080",
        "https://*.mdx.vision"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(transcription.router, prefix="/v1/transcription", tags=["Transcription"])
app.include_router(notes.router, prefix="/v1/notes", tags=["Clinical Notes"])
app.include_router(translation.router, prefix="/v1/translate", tags=["Translation"])
app.include_router(drugs.router, prefix="/v1/drugs", tags=["Drug Interactions"])


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "mdx-ai-pipeline"}


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "MDx Vision AI Pipeline",
        "version": "1.0.0",
        "docs": "/docs"
    }
