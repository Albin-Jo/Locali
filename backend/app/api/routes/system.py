# backend/app/api/routes/system.py

from typing import List, Dict, Any

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from loguru import logger
from pydantic import BaseModel

from ...services.system import SystemDiagnostics, PerformanceMonitor, ModelDownloadManager


# Dependency placeholders - will be overridden in main.py
async def get_system_diagnostics():
    raise NotImplementedError


async def get_performance_monitor():
    raise NotImplementedError


async def get_model_download_manager():
    raise NotImplementedError


# Request/Response Models
class SystemHealthResponse(BaseModel):
    overall_status: str
    timestamp: str
    checks: Dict[str, Any]


class SystemSummaryResponse(BaseModel):
    system: Dict[str, Any]
    performance: Dict[str, Any]
    models: Dict[str, Any]
    services: Dict[str, Any]


class PerformanceMetricsResponse(BaseModel):
    monitoring_active: bool
    metrics_count: int
    last_hour: Dict[str, Any]


class DownloadModelRequest(BaseModel):
    model_name: str


class ModelRepositoryResponse(BaseModel):
    models: List[Dict[str, Any]]


# Router
router = APIRouter(prefix="/system", tags=["system"])


@router.get("/health", response_model=SystemHealthResponse)
async def get_system_health(
        diagnostics: SystemDiagnostics = Depends(get_system_diagnostics)
):
    """Get comprehensive system health status."""
    try:
        health_check = await diagnostics.run_health_check()
        return SystemHealthResponse(**health_check)

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail="Health check failed")


@router.get("/summary", response_model=SystemSummaryResponse)
async def get_system_summary(
        diagnostics: SystemDiagnostics = Depends(get_system_diagnostics)
):
    """Get comprehensive system summary."""
    try:
        summary = diagnostics.get_system_summary()
        return SystemSummaryResponse(**summary)

    except Exception as e:
        logger.error(f"Failed to get system summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to get system summary")


@router.get("/performance", response_model=PerformanceMetricsResponse)
async def get_performance_metrics(
        monitor: PerformanceMonitor = Depends(get_performance_monitor)
):
    """Get performance monitoring metrics."""
    try:
        metrics = monitor.get_metrics_summary()
        return PerformanceMetricsResponse(**metrics)

    except Exception as e:
        logger.error(f"Failed to get performance metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get performance metrics")


@router.post("/performance/start")
async def start_performance_monitoring(
        interval_seconds: int = 30,
        monitor: PerformanceMonitor = Depends(get_performance_monitor)
):
    """Start performance monitoring."""
    try:
        await monitor.start_monitoring(interval_seconds)
        return {"message": f"Performance monitoring started with {interval_seconds}s interval"}

    except Exception as e:
        logger.error(f"Failed to start performance monitoring: {e}")
        raise HTTPException(status_code=500, detail="Failed to start monitoring")


@router.post("/performance/stop")
async def stop_performance_monitoring(
        monitor: PerformanceMonitor = Depends(get_performance_monitor)
):
    """Stop performance monitoring."""
    try:
        await monitor.stop_monitoring()
        return {"message": "Performance monitoring stopped"}

    except Exception as e:
        logger.error(f"Failed to stop performance monitoring: {e}")
        raise HTTPException(status_code=500, detail="Failed to stop monitoring")


@router.get("/models/repository", response_model=ModelRepositoryResponse)
async def get_model_repository(
        download_manager: ModelDownloadManager = Depends(get_model_download_manager)
):
    """Get available models for download."""
    try:
        models = download_manager.list_available_models()
        return ModelRepositoryResponse(models=models)

    except Exception as e:
        logger.error(f"Failed to get model repository: {e}")
        raise HTTPException(status_code=500, detail="Failed to get model repository")


@router.post("/models/download")
async def download_model(
        request: DownloadModelRequest,
        download_manager: ModelDownloadManager = Depends(get_model_download_manager)
):
    """Download a model with streaming progress."""
    try:
        async def generate():
            async for progress in download_manager.download_model(request.model_name):
                import json
                yield f"data: {json.dumps(progress)}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(
            generate(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/plain; charset=utf-8"
            }
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Model download failed: {e}")
        raise HTTPException(status_code=500, detail="Model download failed")


@router.get("/models/download/{model_name}/status")
async def get_download_status(
        model_name: str,
        download_manager: ModelDownloadManager = Depends(get_model_download_manager)
):
    """Get download status for a model."""
    try:
        status = download_manager.get_download_status(model_name)
        return status

    except Exception as e:
        logger.error(f"Failed to get download status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get download status")


@router.post("/models/download/{model_name}/cancel")
async def cancel_model_download(
        model_name: str,
        download_manager: ModelDownloadManager = Depends(get_model_download_manager)
):
    """Cancel an ongoing model download."""
    try:
        success = download_manager.cancel_download(model_name)

        if success:
            return {"message": f"Download of {model_name} cancelled"}
        else:
            raise HTTPException(status_code=404, detail="No active download found")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel download: {e}")
        raise HTTPException(status_code=500, detail="Failed to cancel download")
