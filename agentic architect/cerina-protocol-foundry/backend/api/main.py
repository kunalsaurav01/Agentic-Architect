"""
Cerina Protocol Foundry - FastAPI Application
Main entry point for the backend API.
"""

import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.core.config import settings
from backend.models.database import init_db
from backend.api.routes import router
from backend.api.websocket import manager as ws_manager, handle_websocket_connection


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info("Starting Cerina Protocol Foundry...")
    init_db()
    logger.info("Database initialized")
    yield
    # Shutdown
    logger.info("Shutting down Cerina Protocol Foundry...")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="""
    Cerina Protocol Foundry - Multi-Agent CBT Protocol Design System

    A production-grade autonomous multi-agent system that designs, critiques,
    refines, and safety-checks CBT (Cognitive Behavioral Therapy) exercises
    using a LangGraph architecture with human-in-the-loop control.

    ## Features

    * **Multi-Agent Architecture**: Specialized agents for drafting, clinical review,
      safety validation, and empathy enhancement
    * **Human-in-the-Loop**: Mandatory human approval before protocol finalization
    * **Real-time Updates**: WebSocket support for live agent state streaming
    * **Full Persistence**: Complete checkpointing for resumability
    * **MCP Integration**: Expose as MCP tool for programmatic access
    """,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include API routes
app.include_router(router, prefix=settings.api_prefix, tags=["protocols"])


# WebSocket endpoint
@app.websocket("/ws/{thread_id}")
async def websocket_endpoint(websocket: WebSocket, thread_id: str):
    """
    WebSocket endpoint for real-time updates on a specific protocol.

    Connect to this endpoint with a thread_id to receive:
    - Agent status updates
    - State changes
    - Human review notifications
    - Completion events
    """
    await handle_websocket_connection(websocket, thread_id)


@app.websocket("/ws")
async def websocket_general(websocket: WebSocket):
    """
    General WebSocket endpoint.
    Connect here and subscribe to specific threads as needed.
    """
    await handle_websocket_connection(websocket)


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "health": f"{settings.api_prefix}/health",
        "websocket": "/ws/{{thread_id}}",
    }


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if settings.debug else "An unexpected error occurred",
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.api.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
