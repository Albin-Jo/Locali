# backend/app/main.py

import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from backend.app.api.routes import conversations, models, documents, search, system, tasks
from backend.app.core.config import settings
from backend.app.core.logging import setup_logging
from backend.app.services.background_tasks import (
    BackgroundTaskManager, DocumentProcessingTasks, ModelManagementTasks,
    get_task_manager, shutdown_task_manager
)
from backend.app.services.conversation_manager import ConversationManager
from backend.app.services.document_processor import DocumentProcessor
from backend.app.services.model_manager import ModelManager
from backend.app.services.security import SecurityManager
from backend.app.services.system import SystemDiagnostics, PerformanceMonitor, ModelDownloadManager
from backend.app.services.vector_search import HybridSearchService
from backend.app.utils.helpers import RateLimiter

# Global service instances
model_manager: ModelManager = None
conversation_manager: ConversationManager = None
document_processor: DocumentProcessor = None
search_service: HybridSearchService = None
security_manager: SecurityManager = None
system_diagnostics: SystemDiagnostics = None
performance_monitor: PerformanceMonitor = None
model_download_manager: ModelDownloadManager = None
background_task_manager: BackgroundTaskManager = None
document_processing_tasks: DocumentProcessingTasks = None
model_management_tasks: ModelManagementTasks = None

# Rate limiters
api_rate_limiter = RateLimiter(max_requests=100, window_seconds=60)  # 100 requests per minute
upload_rate_limiter = RateLimiter(max_requests=10, window_seconds=60)  # 10 uploads per minute


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global model_manager, conversation_manager, document_processor
    global search_service, security_manager, system_diagnostics
    global performance_monitor, model_download_manager, background_task_manager
    global document_processing_tasks, model_management_tasks
    # Startup
    logger.info("🚀 Starting CodeAssist AI Backend...")

    # Store start time for uptime calculation
    app.state.start_time = time.time()

    try:
        # Initialize security manager first
        security_manager = SecurityManager()
        logger.info("✅ Security manager initialized")

        # Initialize background task manager
        background_task_manager = await get_task_manager()
        logger.info("✅ Background task manager initialized")

        # Initialize core services
        model_manager = ModelManager()
        conversation_manager = ConversationManager(model_manager)
        logger.info("✅ Core services initialized")

        # Initialize RAG services
        document_processor = DocumentProcessor()
        search_service = HybridSearchService()
        logger.info("✅ RAG services initialized")

        # Initialize system services
        performance_monitor = PerformanceMonitor()
        model_download_manager = ModelDownloadManager()
        system_diagnostics = SystemDiagnostics()
        logger.info("✅ System services initialized")

        # Initialize specialized task processors
        document_processing_tasks = DocumentProcessingTasks(background_task_manager)
        model_management_tasks = ModelManagementTasks(background_task_manager)
        logger.info("✅ Task processors initialized")

        # Start performance monitoring (unless in debug mode)
        if not settings.debug:
            await performance_monitor.start_monitoring(interval_seconds=60)
            logger.info("✅ Performance monitoring started")

        # Load default model if available
        try:
            available_models = await model_manager.list_available_models()
            default_model_exists = (
                    settings.default_model in available_models and
                    available_models[settings.default_model]['exists']
            )

            if default_model_exists:
                await model_manager.load_model(settings.default_model)
                logger.success(f"✅ Default model '{settings.default_model}' loaded successfully")
            else:
                logger.warning(f"⚠️  Default model '{settings.default_model}' not found")

        except Exception as e:
            logger.warning(f"⚠️  Failed to load default model: {e}")

        # Run initial health check
        try:
            health_status = await system_diagnostics.run_health_check()
            if health_status['overall_status'] == 'ok':
                logger.success("✅ System health check passed")
            else:
                logger.warning(f"⚠️  System health check: {health_status['overall_status']}")
        except Exception as e:
            logger.error(f"❌ Health check failed: {e}")

        logger.success("🎉 Backend startup complete!")

    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        raise

    yield

    # Shutdown
    logger.info("🛑 Shutting down CodeAssist AI Backend...")

    try:
        # Stop monitoring
        if performance_monitor and performance_monitor.monitoring_active:
            await performance_monitor.stop_monitoring()
            logger.info("✅ Performance monitoring stopped")

        # Shutdown background tasks
        await shutdown_task_manager()
        logger.info("✅ Background task manager shutdown")

        # Cleanup models
        if model_manager:
            for model_name in list(model_manager.models.keys()):
                await model_manager.unload_model(model_name)
            logger.info("✅ Models unloaded")

        logger.success("🎉 Backend shutdown complete!")

    except Exception as e:
        logger.error(f"❌ Shutdown error: {e}")


# Initialize FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Local AI coding assistant backend with RAG capabilities and background task processing",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None
)

# Setup logging
setup_logging()

# Middleware

# Security middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["localhost", "127.0.0.1", "::1"]
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Rate limiting middleware
@app.middleware("http")
async def rate_limiting_middleware(request: Request, call_next):
    """Apply rate limiting to API requests."""
    # Get client identifier (simplified - in production would use proper client identification)
    client_id = request.client.host if request.client else "unknown"

    # Different rate limits for different endpoints
    path = request.url.path

    # Upload endpoints have stricter limits
    if "/upload" in path or "/documents" in path and request.method == "POST":
        if not upload_rate_limiter.is_allowed(client_id):
            return JSONResponse(
                status_code=429,
                content={"detail": "Upload rate limit exceeded"}
            )
    else:
        # General API rate limiting
        if not api_rate_limiter.is_allowed(client_id):
            return JSONResponse(
                status_code=429,
                content={"detail": "API rate limit exceeded"}
            )

    return await call_next(request)


# Performance logging middleware
@app.middleware("http")
async def performance_middleware(request: Request, call_next):
    """Log request performance."""
    start_time = time.perf_counter()

    response = await call_next(request)

    process_time = time.perf_counter() - start_time

    # Log slow requests
    if process_time > 3.0:
        logger.warning(
            f"🐌 Slow request: {request.method} {request.url.path} "
            f"took {process_time:.3f}s"
        )
    elif process_time > 1.0:
        logger.info(
            f"⏱️  {request.method} {request.url.path} took {process_time:.3f}s"
        )

    # Add performance header
    response.headers["X-Process-Time"] = str(process_time)

    return response


# Security validation middleware
@app.middleware("http")
async def security_middleware(request: Request, call_next):
    """Validate requests against security policies."""
    if security_manager:
        # Get request data for validation
        request_data = {
            "method": request.method,
            "url": str(request.url),
            "headers": dict(request.headers)
        }

        # Basic security validation
        is_safe = security_manager.validate_request_security(request_data)

        if not is_safe:
            logger.warning(f"🔒 Blocked unsafe request: {request.method} {request.url.path}")
            return JSONResponse(
                status_code=400,
                content={"detail": "Request blocked by security policy"}
            )

    return await call_next(request)


# Dependency injection functions
async def get_model_manager():
    return model_manager


async def get_conversation_manager():
    return conversation_manager


async def get_document_processor():
    return document_processor


async def get_search_service():
    return search_service


async def get_security_manager():
    return security_manager


async def get_system_diagnostics():
    return system_diagnostics


async def get_performance_monitor():
    return performance_monitor


async def get_model_download_manager():
    return model_download_manager


async def get_background_task_manager():
    return background_task_manager


async def get_document_processing_tasks():
    return document_processing_tasks


async def get_model_management_tasks():
    return model_management_tasks


# Override route dependencies
conversations.get_model_manager = get_model_manager
conversations.get_conversation_manager = get_conversation_manager

models.get_model_manager = get_model_manager

documents.get_document_processor = get_document_processor
documents.get_search_service = get_search_service

search.get_search_service = get_search_service

system.get_system_diagnostics = get_system_diagnostics
system.get_performance_monitor = get_performance_monitor
system.get_model_download_manager = get_model_download_manager

tasks.get_background_task_manager = get_background_task_manager

# Include routers
app.include_router(conversations.router, prefix="/api/v1")
app.include_router(models.router, prefix="/api/v1")
app.include_router(documents.router, prefix="/api/v1")
app.include_router(search.router, prefix="/api/v1")
app.include_router(system.router, prefix="/api/v1")
app.include_router(tasks.router, prefix="/api/v1")


# Root endpoints
@app.get("/")
async def root():
    """Root endpoint with feature overview."""
    return {
        "message": "CodeAssist AI Backend",
        "version": settings.app_version,
        "status": "healthy",
        "description": "Local AI coding assistant with privacy-first architecture",
        "features": {
            "core": [
                "LLM Inference with streaming",
                "Conversation management",
                "Model switching and management"
            ],
            "rag": [
                "Document processing and chunking",
                "Hybrid vector + keyword search",
                "Multi-language code parsing"
            ],
            "system": [
                "Performance monitoring",
                "Background task processing",
                "System diagnostics"
            ],
            "security": [
                "Network isolation",
                "Optional encryption",
                "Rate limiting"
            ]
        },
        "endpoints": {
            "conversations": "/api/v1/conversations",
            "models": "/api/v1/models",
            "documents": "/api/v1/documents",
            "search": "/api/v1/search",
            "system": "/api/v1/system",
            "tasks": "/api/v1/tasks"
        }
    }


@app.get("/health")
async def health_check():
    """Comprehensive health check endpoint."""
    try:
        health_data = {
            "status": "healthy",
            "version": settings.app_version,
            "timestamp": time.time(),
            "uptime_seconds": time.time() - app.state.start_time if hasattr(app.state, 'start_time') else 0,
            "services": {
                "model_manager": model_manager is not None,
                "model_loaded": model_manager.current_model is not None if model_manager else False,
                "conversation_manager": conversation_manager is not None,
                "document_processor": document_processor is not None,
                "search_service": search_service is not None,
                "security_manager": security_manager is not None,
                "performance_monitor": performance_monitor is not None and performance_monitor.monitoring_active if performance_monitor else False,
                "background_tasks": background_task_manager is not None
            }
        }

        # Add system metrics
        if performance_monitor:
            try:
                current_metrics = await performance_monitor.collect_metrics()
                health_data["system_metrics"] = {
                    "cpu_percent": current_metrics.cpu_percent,
                    "memory_percent": current_metrics.memory_percent,
                    "memory_available_gb": current_metrics.memory_available_gb,
                    "disk_usage_percent": current_metrics.disk_usage_percent
                }
            except:
                health_data["system_metrics"] = {"error": "metrics_unavailable"}

        # Add task statistics
        if background_task_manager:
            try:
                all_tasks = background_task_manager.get_all_tasks()
                health_data["background_tasks"] = {
                    "total": len(all_tasks),
                    "running": len([t for t in all_tasks if t.status == 'running']),
                    "completed": len([t for t in all_tasks if t.status == 'completed']),
                    "failed": len([t for t in all_tasks if t.status == 'failed'])
                }
            except:
                health_data["background_tasks"] = {"error": "tasks_unavailable"}

        return health_data

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "version": settings.app_version,
                "timestamp": time.time()
            }
        )


# Rest of the endpoints remain the same...
# (truncated for brevity)


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error(f"❌ Unhandled exception in {request.method} {request.url.path}: {exc}")

    # Don't expose internal errors in production
    if settings.debug:
        detail = str(exc)
    else:
        detail = "Internal server error"

    return JSONResponse(
        status_code=500,
        content={
            "detail": detail,
            "timestamp": time.time(),
            "path": str(request.url.path)
        }
    )


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Enhanced 404 handler with helpful information."""
    return JSONResponse(
        status_code=404,
        content={
            "detail": f"Endpoint {request.url.path} not found",
            "available_endpoints": {
                "conversations": "/api/v1/conversations - Manage AI conversations",
                "models": "/api/v1/models - Model management and switching",
                "documents": "/api/v1/documents - Document upload and processing",
                "search": "/api/v1/search - Search through documents",
                "system": "/api/v1/system - System health and diagnostics",
                "tasks": "/api/v1/tasks - Background task monitoring"
            },
            "documentation": "/docs" if settings.debug else "Documentation disabled in production"
        }
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,  # This should now correctly use 8080
        reload=settings.reload,
        log_level=settings.log_level.lower(),
        access_log=settings.debug
    )