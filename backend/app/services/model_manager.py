# backend/app/services/model_manager.py

import asyncio
from pathlib import Path
from typing import Optional, Dict, AsyncIterator

import psutil
from loguru import logger

from ..core.config import settings, get_model_config, get_system_info
from ..core.logging import log_performance, log_model_operation


class ModelNotFoundError(Exception):
    """Raised when a requested model is not found."""
    pass


class ModelLoadError(Exception):
    """Raised when a model fails to load."""
    pass


class InsufficientMemoryError(Exception):
    """Raised when system doesn't have enough memory for model."""
    pass


class LlamaModel:
    """Wrapper for llama-cpp-python model."""

    def __init__(self, model_path: str, config: dict):
        self.model_path = model_path
        self.config = config
        self.model = None
        self.is_loaded = False
        self.memory_usage_mb = 0

    @log_performance("model_load")
    async def load(self):
        """Load the model into memory."""
        try:
            # Import here to avoid dependency issues if not installed
            from llama_cpp import Llama

            # Check memory requirements
            await self._check_memory_requirements()

            # Configure model parameters
            model_params = {
                "model_path": self.model_path,
                "n_ctx": min(self.config["context_length"], settings.max_context_length),
                "n_threads": settings.cpu_threads,
                "verbose": False,
                "use_mmap": True,
                "use_mlock": False,
                "n_batch": 512,
            }

            # GPU configuration
            if settings.use_gpu and self.config.get("gpu_layers", 0) > 0:
                model_params["n_gpu_layers"] = self.config["gpu_layers"]

            log_func = log_model_operation("load", Path(self.model_path).stem)
            log_func("Loading model with llama.cpp")

            # Load model in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            self.model = await loop.run_in_executor(
                None, lambda: Llama(**model_params)
            )

            self.is_loaded = True
            self.memory_usage_mb = self._estimate_memory_usage()

            log_func(f"Model loaded successfully ({self.memory_usage_mb}MB)")
            return True

        except ImportError:
            raise ModelLoadError("llama-cpp-python not installed. Run: pip install llama-cpp-python")
        except Exception as e:
            logger.error(f"Failed to load model {self.model_path}: {e}")
            raise ModelLoadError(f"Failed to load model: {e}")

    async def unload(self):
        """Unload the model from memory."""
        if self.model:
            log_func = log_model_operation("unload", Path(self.model_path).stem)
            log_func("Unloading model")

            # Clean up model
            del self.model
            self.model = None
            self.is_loaded = False
            self.memory_usage_mb = 0

            # Force garbage collection
            import gc
            gc.collect()

            log_func("Model unloaded")

    async def generate_stream(
            self,
            prompt: str,
            max_tokens: int = 512,
            temperature: float = None,
            top_p: float = None,
            stop: list = None
    ) -> AsyncIterator[str]:
        """Generate streaming response."""
        if not self.is_loaded:
            raise ModelLoadError("Model not loaded")

        # Use model defaults if not specified
        temperature = temperature or self.config.get("temperature", 0.7)
        top_p = top_p or self.config.get("top_p", 0.9)
        stop = stop or ["</s>", "<|endoftext|>", "\n\n"]

        try:
            # Generate tokens
            stream = self.model(
                prompt,
                max_tokens=min(max_tokens, settings.max_tokens_per_request),
                temperature=temperature,
                top_p=top_p,
                stop=stop,
                stream=True,
                echo=False
            )

            for output in stream:
                token = output.get("choices", [{}])[0].get("text", "")
                if token:
                    yield token

        except Exception as e:
            logger.error(f"Generation failed: {e}")
            raise

    async def _check_memory_requirements(self):
        """Check if system has enough memory for model."""
        required_mb = self.config.get("recommended_ram_gb", 8) * 1024
        available_mb = psutil.virtual_memory().available // (1024 * 1024)

        if available_mb < required_mb:
            raise InsufficientMemoryError(
                f"Model requires {required_mb}MB, only {available_mb}MB available"
            )

    def _estimate_memory_usage(self) -> int:
        """Estimate current memory usage of the model."""
        if not self.is_loaded:
            return 0

        # Basic estimation - could be improved with actual measurement
        return self.config.get("recommended_ram_gb", 8) * 1024


def _check_llama_availability() -> bool:
    """Check if llama-cpp-python is available."""
    try:
        import llama_cpp
        return True
    except ImportError:
        return False


class ModelManager:
    """Manages multiple LLM models with memory-efficient loading."""

    def __init__(self):
        self.models: Dict[str, LlamaModel] = {}
        self.current_model: Optional[str] = None
        self.models_dir = settings.models_dir
        self.max_memory_mb = settings.max_memory_gb * 1024
        self._llama_available = _check_llama_availability()

        logger.info(f"ModelManager initialized - Models dir: {self.models_dir}")

        if not self._llama_available:
            logger.warning("⚠️  llama-cpp-python not available. Model loading will fail.")
            logger.info("Install with: pip install llama-cpp-python")

    async def list_available_models(self) -> Dict[str, dict]:
        """List all available models with their info."""
        available = {}

        for model_name in ["phi-3.5-mini", "qwen2.5-coder-7b", "deepseek-coder-33b"]:
            config = get_model_config(model_name)
            model_path = self.models_dir / config["model_file"]

            available[model_name] = {
                "name": model_name,
                "path": str(model_path),
                "exists": model_path.exists(),
                "size_mb": model_path.stat().st_size // (1024 * 1024) if model_path.exists() else 0,
                "config": config,
                "loaded": model_name in self.models and self.models[model_name].is_loaded,
                "llama_available": self._llama_available
            }

        return available

    async def load_model(self, model_name: str) -> bool:
        """Load a specific model with proper error handling."""
        if not self._llama_available:
            raise ModelLoadError(
                "llama-cpp-python not installed. Install with: pip install llama-cpp-python"
            )

        if model_name in self.models and self.models[model_name].is_loaded:
            logger.info(f"Model {model_name} already loaded")
            self.current_model = model_name
            return True

        # Get model configuration
        config = get_model_config(model_name)
        model_path = self.models_dir / config["model_file"]

        if not model_path.exists():
            raise ModelNotFoundError(
                f"Model file not found: {model_path}. "
                f"Download the model or check the models directory."
            )

        # Check if we need to free memory
        await self._ensure_memory_available(config)

        # Create and load model
        try:
            model = LlamaModel(str(model_path), config)
            await model.load()

            self.models[model_name] = model
            self.current_model = model_name

            logger.info(f"✅ Model {model_name} loaded successfully")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to load model {model_name}: {e}")
            raise ModelLoadError(f"Failed to load model {model_name}: {str(e)}")

    async def unload_model(self, model_name: str) -> bool:
        """Unload a specific model."""
        if model_name not in self.models:
            logger.warning(f"Model {model_name} not loaded")
            return False

        await self.models[model_name].unload()
        del self.models[model_name]

        if self.current_model == model_name:
            # Set another loaded model as current, or None
            self.current_model = next(
                (name for name, model in self.models.items() if model.is_loaded),
                None
            )

        logger.info(f"Model {model_name} unloaded")
        return True

    async def switch_model(self, model_name: str) -> bool:
        """Switch to a different model (load if necessary)."""
        if model_name == self.current_model:
            return True

        # Load the new model if not already loaded
        if model_name not in self.models or not self.models[model_name].is_loaded:
            await self.load_model(model_name)
        else:
            self.current_model = model_name

        logger.info(f"Switched to model: {model_name}")
        return True

    async def generate_stream(
            self,
            prompt: str,
            model_name: str = None,
            **kwargs
    ) -> AsyncIterator[str]:
        """Generate streaming response with better error handling."""
        target_model = model_name or self.current_model

        if not target_model:
            raise ModelLoadError("No model loaded. Load a model first.")

        if not self._llama_available:
            raise ModelLoadError("llama-cpp-python not available")

        if target_model not in self.models or not self.models[target_model].is_loaded:
            try:
                await self.load_model(target_model)
            except Exception as e:
                logger.error(f"Failed to load model for generation: {e}")
                # Yield error message instead of raising
                yield f"Error: Failed to load model {target_model}. {str(e)}"
                return

        try:
            async for token in self.models[target_model].generate_stream(prompt, **kwargs):
                yield token
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            yield f"Error: Generation failed - {str(e)}"

    async def _ensure_memory_available(self, model_config: dict):
        """Ensure enough memory is available for loading model."""
        required_mb = model_config.get("recommended_ram_gb", 8) * 1024
        current_usage = sum(model.memory_usage_mb for model in self.models.values())
        available_mb = self.max_memory_mb - current_usage

        # Unload models if necessary (LRU strategy)
        while available_mb < required_mb and self.models:
            # Find least recently used model (simplified - just unload first)
            lru_model = next(iter(self.models.keys()))
            logger.info(f"Freeing memory by unloading {lru_model}")
            await self.unload_model(lru_model)

            current_usage = sum(model.memory_usage_mb for model in self.models.values())
            available_mb = self.max_memory_mb - current_usage

    async def get_model_info(self, model_name: str = None) -> dict:
        """Get information about current or specified model."""
        target_model = model_name or self.current_model

        if not target_model:
            return {"error": "No model specified or loaded"}

        if target_model not in self.models:
            return {"error": f"Model {target_model} not loaded"}

        model = self.models[target_model]
        return {
            "name": target_model,
            "loaded": model.is_loaded,
            "memory_usage_mb": model.memory_usage_mb,
            "config": model.config,
            "path": model.model_path
        }

    async def get_system_status(self) -> dict:
        """Get system and model status."""
        system_info = get_system_info()
        current_usage = sum(model.memory_usage_mb for model in self.models.values())

        return {
            "system": system_info,
            "memory": {
                "total_mb": self.max_memory_mb,
                "used_by_models_mb": current_usage,
                "available_mb": self.max_memory_mb - current_usage,
                "system_available_mb": psutil.virtual_memory().available // (1024 * 1024)
            },
            "models": {
                "loaded": list(self.models.keys()),
                "current": self.current_model,
                "count": len(self.models)
            }
        }
