import os
from pathlib import Path
from typing import Optional, List

from pydantic import Field, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # Application Info
    app_name: str = "CodeAssist AI"
    app_version: str = "0.1.0"

    # Server Configuration
    host: str = Field(default="localhost", description="Server host")
    port: int = Field(default=8080, description="Server port")
    reload: bool = Field(default=True, description="Auto-reload on code changes")

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    log_file: Optional[str] = Field(default=None, description="Log file path")

    # Model Configuration
    models_dir: Path = Field(default=Path("models"), description="Directory to store models")
    default_model: str = Field(default="phi-3.5-mini", description="Default model to load")
    max_models_loaded: int = Field(default=2, description="Maximum models to keep in memory")

    # Performance Settings
    max_memory_gb: int = Field(default=16, description="Maximum memory usage in GB")
    max_context_length: int = Field(default=8192, description="Maximum context length")
    max_tokens_per_request: int = Field(default=4096, description="Maximum tokens per request")

    # Database Configuration
    database_url: str = Field(default="data/locali.db", description="Database file path")
    vector_db_path: str = Field(default="data/vectors", description="Vector database path")

    # Security Settings
    enable_network_isolation: bool = Field(default=True, description="Block network access")
    enable_conversation_encryption: bool = Field(default=False, description="Encrypt stored conversations")
    allowed_domains: List[str] = Field(default=[], description="Allowed domains for network access")

    # Performance Optimization
    use_gpu: bool = Field(default=True, description="Use GPU acceleration if available")
    gpu_layers: int = Field(default=-1, description="Number of layers to offload to GPU (-1 for auto)")
    cpu_threads: Optional[int] = Field(default=None, description="Number of CPU threads (None for auto)")

    # Development Settings
    debug: bool = Field(default=False, description="Enable debug mode")
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173"],
        description="CORS allowed origins"
    )

    @validator("models_dir", pre=True)
    def validate_models_dir(cls, v):
        """Ensure models directory exists."""
        path = Path(v)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @validator("database_url", pre=True)
    def validate_database_path(cls, v):
        """Ensure database directory exists."""
        path = Path(v)
        path.parent.mkdir(parents=True, exist_ok=True)
        return str(path)

    @validator("vector_db_path", pre=True)
    def validate_vector_db_path(cls, v):
        """Ensure vector database directory exists."""
        path = Path(v)
        path.mkdir(parents=True, exist_ok=True)
        return str(path)

    @validator("cpu_threads", pre=True)
    def validate_cpu_threads(cls, v):
        """Set CPU threads to system CPU count if None."""
        if v is None:
            return os.cpu_count()
        return v

    class Config:
        env_file = ".env"
        env_prefix = "LOCALI_"
        case_sensitive = False


# Global settings instance
settings = Settings()


def get_model_config(model_name: str) -> dict:
    """Get model-specific configuration."""
    model_configs = {
        "phi-3.5-mini": {
            "model_file": "phi-3.5-mini-instruct-q4_k_m.gguf",
            "context_length": 131072,  # 128k context
            "recommended_ram_gb": 8,
            "gpu_layers": 32,
            "temperature": 0.7,
            "top_p": 0.9,
        },
        "qwen2.5-coder-7b": {
            "model_file": "qwen2.5-coder-7b-instruct-q4_k_m.gguf",
            "context_length": 32768,  # 32k context
            "recommended_ram_gb": 16,
            "gpu_layers": 40,
            "temperature": 0.3,  # Lower for code generation
            "top_p": 0.95,
        },
        "deepseek-coder-33b": {
            "model_file": "deepseek-coder-33b-instruct-q4_k_m.gguf",
            "context_length": 16384,  # 16k context
            "recommended_ram_gb": 32,
            "gpu_layers": 60,
            "temperature": 0.2,  # Very low for code
            "top_p": 0.95,
        }
    }

    return model_configs.get(model_name, model_configs["phi-3.5-mini"])


def get_system_info() -> dict:
    """Get system information for model selection."""
    import psutil
    import platform

    # Get available RAM
    ram_gb = psutil.virtual_memory().total // (1024 ** 3)

    # Detect GPU
    gpu_info = None
    try:
        # Try to detect NVIDIA GPU
        import pynvml
        pynvml.nvmlInit()
        gpu_count = pynvml.nvmlDeviceGetCount()
        if gpu_count > 0:
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            gpu_name = pynvml.nvmlDeviceGetName(handle).decode()
            gpu_memory = pynvml.nvmlDeviceGetMemoryInfo(handle).total // (1024 ** 2)  # MB
            gpu_info = {"name": gpu_name, "memory_mb": gpu_memory, "type": "nvidia"}
    except:
        # Check for Apple Silicon
        if platform.machine() == "arm64" and platform.system() == "Darwin":
            gpu_info = {"name": "Apple Silicon", "memory_mb": None, "type": "apple"}

    return {
        "ram_gb": ram_gb,
        "cpu_count": os.cpu_count(),
        "platform": platform.system(),
        "architecture": platform.machine(),
        "gpu": gpu_info
    }


def recommend_model() -> str:
    """Recommend the best model for the current system."""
    system = get_system_info()
    ram_gb = system["ram_gb"]

    if ram_gb >= 32:
        return "deepseek-coder-33b"
    elif ram_gb >= 16:
        return "qwen2.5-coder-7b"
    else:
        return "phi-3.5-mini"
