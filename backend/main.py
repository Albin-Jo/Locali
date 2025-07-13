import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from app.core.config import settings
from app.core.logging import setup_logging
from app.services.model_manager import ModelManager
from app.services.conversation_manager import ConversationManager
from app.api.routes import conversations, models

# Global service instances
model_manager: ModelManager = None
conversation_manager: ConversationManager = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global model_manager, conversation_manager

    # Startup
    logger.info("Starting CodeAssist AI Backend...")

    # Initialize services
    model_manager = ModelManager()
    conversation_manager = ConversationManager(model_manager)

    # Load default model
    try:
        await model_manager.load_model(settings.default_model)
        logger.success("Default model loaded successfully")
    except Exception as e:
        logger.warning(f"Failed to load default model: {e}")

    logger.success("Backend startup complete")

    yield

    # Shutdown
    logger.info("Shutting down CodeAssist AI Backend...")

    # Cleanup
    if model_manager:
        for model_name in list(model_manager.models.keys()):
            await model_manager.unload_model(model_name)

    logger.success("Backend shutdown complete")


# Initialize FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Local AI coding assistant backend",
    lifespan=lifespan
)

# Setup logging
setup_logging()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Dependency injection
async def get_model_manager():
    return model_manager


async def get_conversation_manager():
    return conversation_manager


# Override route dependencies
conversations.get_model_manager = get_model_manager
conversations.get_conversation_manager = get_conversation_manager
models.get_model_manager = get_model_manager

# Include routers
app.include_router(conversations.router, prefix="/api/v1")
app.include_router(models.router, prefix="/api/v1")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "CodeAssist AI Backend",
        "version": settings.app_version,
        "status": "healthy"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": settings.app_version,
        "model_loaded": model_manager.current_model is not None if model_manager else False
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level=settings.log_level.lower()
    )
