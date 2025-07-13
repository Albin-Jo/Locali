from typing import List, Dict, Any, Optional

from fastapi import APIRouter, HTTPException, Depends
from loguru import logger
from pydantic import BaseModel

from ...core.config import get_system_info, recommend_model
from ...services.model_manager import ModelManager, ModelNotFoundError, ModelLoadError, InsufficientMemoryError


# Dependency placeholder - will be overridden in main.py
async def get_model_manager():
    raise NotImplementedError


# Request/Response Models
class LoadModelRequest(BaseModel):
    model_name: str


class ModelInfoResponse(BaseModel):
    name: str
    loaded: bool
    exists: bool
    size_mb: int
    memory_usage_mb: Optional[int] = None
    config: Dict[str, Any]
    path: str


class SystemStatusResponse(BaseModel):
    system: Dict[str, Any]
    memory: Dict[str, Any]
    models: Dict[str, Any]
    recommendations: Dict[str, str]


class ModelOperationResponse(BaseModel):
    success: bool
    message: str
    model_name: Optional[str] = None


# Router
router = APIRouter(prefix="/models", tags=["models"])


@router.get("/", response_model=List[ModelInfoResponse])
async def list_models(
        model_manager: ModelManager = Depends(get_model_manager)
):
    """List all available models with their status."""
    try:
        models = await model_manager.list_available_models()

        return [
            ModelInfoResponse(
                name=name,
                loaded=info['loaded'],
                exists=info['exists'],
                size_mb=info['size_mb'],
                memory_usage_mb=None if not info['loaded'] else info['config'].get('recommended_ram_gb', 0) * 1024,
                config=info['config'],
                path=info['path']
            )
            for name, info in models.items()
        ]

    except Exception as e:
        logger.error(f"Failed to list models: {e}")
        raise HTTPException(status_code=500, detail="Failed to list models")


@router.get("/current")
async def get_current_model(
        model_manager: ModelManager = Depends(get_model_manager)
):
    """Get information about the currently loaded model."""
    try:
        if not model_manager.current_model:
            return {"message": "No model currently loaded"}

        model_info = await model_manager.get_model_info()
        return model_info

    except Exception as e:
        logger.error(f"Failed to get current model info: {e}")
        raise HTTPException(status_code=500, detail="Failed to get current model info")


@router.post("/load", response_model=ModelOperationResponse)
async def load_model(
        request: LoadModelRequest,
        model_manager: ModelManager = Depends(get_model_manager)
):
    """Load a specific model."""
    try:
        success = await model_manager.load_model(request.model_name)

        return ModelOperationResponse(
            success=success,
            message=f"Model {request.model_name} loaded successfully",
            model_name=request.model_name
        )

    except ModelNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    except InsufficientMemoryError as e:
        raise HTTPException(status_code=400, detail=str(e))

    except ModelLoadError as e:
        raise HTTPException(status_code=500, detail=str(e))

    except Exception as e:
        logger.error(f"Failed to load model {request.model_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load model: {str(e)}")


@router.post("/unload/{model_name}", response_model=ModelOperationResponse)
async def unload_model(
        model_name: str,
        model_manager: ModelManager = Depends(get_model_manager)
):
    """Unload a specific model."""
    try:
        success = await model_manager.unload_model(model_name)

        if not success:
            return ModelOperationResponse(
                success=False,
                message=f"Model {model_name} was not loaded",
                model_name=model_name
            )

        return ModelOperationResponse(
            success=success,
            message=f"Model {model_name} unloaded successfully",
            model_name=model_name
        )

    except Exception as e:
        logger.error(f"Failed to unload model {model_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to unload model: {str(e)}")


@router.post("/switch/{model_name}", response_model=ModelOperationResponse)
async def switch_model(
        model_name: str,
        model_manager: ModelManager = Depends(get_model_manager)
):
    """Switch to a different model (load if necessary)."""
    try:
        success = await model_manager.switch_model(model_name)

        return ModelOperationResponse(
            success=success,
            message=f"Switched to model {model_name}",
            model_name=model_name
        )

    except ModelNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    except InsufficientMemoryError as e:
        raise HTTPException(status_code=400, detail=str(e))

    except ModelLoadError as e:
        raise HTTPException(status_code=500, detail=str(e))

    except Exception as e:
        logger.error(f"Failed to switch to model {model_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to switch model: {str(e)}")


@router.get("/status", response_model=SystemStatusResponse)
async def get_system_status(
        model_manager: ModelManager = Depends(get_model_manager)
):
    """Get system status including models, memory, and recommendations."""
    try:
        # Get system status from model manager
        status = await model_manager.get_system_status()

        # Add recommendations
        recommended_model = recommend_model()
        system_info = get_system_info()

        recommendations = {
            "recommended_model": recommended_model,
            "reason": f"Based on {system_info['ram_gb']}GB RAM"
        }

        # Add GPU recommendations
        if system_info.get('gpu'):
            gpu = system_info['gpu']
            if gpu['type'] == 'nvidia' and gpu.get('memory_mb', 0) > 8000:
                recommendations["gpu_optimization"] = "NVIDIA GPU detected - GPU acceleration enabled"
            elif gpu['type'] == 'apple':
                recommendations["gpu_optimization"] = "Apple Silicon detected - MLX optimization available"
        else:
            recommendations["gpu_optimization"] = "No GPU detected - using CPU inference"

        return SystemStatusResponse(
            system=status['system'],
            memory=status['memory'],
            models=status['models'],
            recommendations=recommendations
        )

    except Exception as e:
        logger.error(f"Failed to get system status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get system status")


@router.get("/{model_name}/info")
async def get_model_info(
        model_name: str,
        model_manager: ModelManager = Depends(get_model_manager)
):
    """Get detailed information about a specific model."""
    try:
        model_info = await model_manager.get_model_info(model_name)

        if "error" in model_info:
            raise HTTPException(status_code=404, detail=model_info["error"])

        return model_info

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get model info for {model_name}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get model info")


@router.get("/recommendations")
async def get_model_recommendations():
    """Get model recommendations based on system capabilities."""
    try:
        system_info = get_system_info()
        recommended = recommend_model()

        # Create detailed recommendations
        recommendations = {
            "system_info": system_info,
            "recommended_model": recommended,
            "all_models": {}
        }

        # Add info for each model tier
        models_info = {
            "phi-3.5-mini": {
                "tier": "Minimal (8-12GB RAM)",
                "best_for": "Quick responses, basic coding help",
                "pros": ["Fast inference", "Low memory usage", "Good for simple tasks"],
                "cons": ["Limited reasoning", "Smaller context window"]
            },
            "qwen2.5-coder-7b": {
                "tier": "Standard (16-24GB RAM)",
                "best_for": "Code generation, debugging, explanations",
                "pros": ["Balanced performance", "Good code quality", "Reasonable speed"],
                "cons": ["Higher memory usage", "May struggle with complex tasks"]
            },
            "deepseek-coder-33b": {
                "tier": "Premium (32GB+ RAM)",
                "best_for": "Complex architectures, advanced debugging",
                "pros": ["Excellent code quality", "Deep reasoning", "Complex problem solving"],
                "cons": ["High memory usage", "Slower inference", "Requires powerful hardware"]
            }
        }

        for model_name, info in models_info.items():
            recommendations["all_models"][model_name] = {
                **info,
                "compatible": system_info["ram_gb"] >= (8 if "mini" in model_name else 16 if "7b" in model_name else 32)
            }

        return recommendations

    except Exception as e:
        logger.error(f"Failed to get recommendations: {e}")
        raise HTTPException(status_code=500, detail="Failed to get recommendations")
