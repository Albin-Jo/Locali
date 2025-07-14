# backend/app/services/system.py

import asyncio
import platform
import psutil
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, AsyncIterator
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import aiohttp
import aiofiles
from urllib.parse import urlparse

from loguru import logger
from ..core.config import settings, get_system_info, get_model_config
from ..core.logging import log_performance


@dataclass
class SystemMetrics:
    """System performance metrics."""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_used_gb: float
    memory_available_gb: float
    disk_usage_percent: float
    gpu_memory_used_mb: Optional[float] = None
    gpu_memory_total_mb: Optional[float] = None
    gpu_utilization_percent: Optional[float] = None

    def to_dict(self) -> dict:
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data


@dataclass
class ModelDownloadInfo:
    """Information about downloadable models."""
    name: str
    display_name: str
    size_gb: float
    download_url: str
    checksum: str
    description: str
    requirements: Dict[str, Any]
    tags: List[str]

    def to_dict(self) -> dict:
        return asdict(self)


class PerformanceMonitor:
    """Monitors system performance metrics."""

    def __init__(self):
        self.metrics_history: List[SystemMetrics] = []
        self.max_history_size = 1000  # Keep last 1000 metrics
        self.monitoring_active = False
        self.monitor_task: Optional[asyncio.Task] = None

        # Performance thresholds
        self.cpu_warning_threshold = 80.0
        self.memory_warning_threshold = 85.0
        self.gpu_memory_warning_threshold = 90.0

        logger.info("PerformanceMonitor initialized")

    async def start_monitoring(self, interval_seconds: int = 30):
        """Start continuous performance monitoring."""
        if self.monitoring_active:
            return

        self.monitoring_active = True
        self.monitor_task = asyncio.create_task(self._monitor_loop(interval_seconds))
        logger.info(f"Performance monitoring started (interval: {interval_seconds}s)")

    async def stop_monitoring(self):
        """Stop performance monitoring."""
        self.monitoring_active = False
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("Performance monitoring stopped")

    async def _monitor_loop(self, interval_seconds: int):
        """Main monitoring loop."""
        while self.monitoring_active:
            try:
                metrics = await self.collect_metrics()
                self.metrics_history.append(metrics)

                # Trim history if too long
                if len(self.metrics_history) > self.max_history_size:
                    self.metrics_history = self.metrics_history[-self.max_history_size:]

                # Check for performance warnings
                await self._check_performance_warnings(metrics)

                await asyncio.sleep(interval_seconds)

            except Exception as e:
                logger.error(f"Performance monitoring error: {e}")
                await asyncio.sleep(interval_seconds)

    async def collect_metrics(self) -> SystemMetrics:
        """Collect current system metrics."""
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)

        # Memory usage
        memory = psutil.virtual_memory()
        memory_used_gb = (memory.total - memory.available) / (1024 ** 3)
        memory_available_gb = memory.available / (1024 ** 3)

        # Disk usage
        disk = psutil.disk_usage('/')
        disk_usage_percent = (disk.used / disk.total) * 100

        # GPU metrics (if available)
        gpu_memory_used_mb = None
        gpu_memory_total_mb = None
        gpu_utilization_percent = None

        try:
            gpu_info = await self._get_gpu_metrics()
            if gpu_info:
                gpu_memory_used_mb = gpu_info.get('memory_used_mb')
                gpu_memory_total_mb = gpu_info.get('memory_total_mb')
                gpu_utilization_percent = gpu_info.get('utilization_percent')
        except:
            pass  # GPU metrics not available

        return SystemMetrics(
            timestamp=datetime.now(),
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            memory_used_gb=memory_used_gb,
            memory_available_gb=memory_available_gb,
            disk_usage_percent=disk_usage_percent,
            gpu_memory_used_mb=gpu_memory_used_mb,
            gpu_memory_total_mb=gpu_memory_total_mb,
            gpu_utilization_percent=gpu_utilization_percent
        )

    async def _get_gpu_metrics(self) -> Optional[Dict[str, Any]]:
        """Get GPU metrics if available."""
        try:
            # Try NVIDIA first
            import pynvml
            pynvml.nvmlInit()

            device_count = pynvml.nvmlDeviceGetCount()
            if device_count > 0:
                handle = pynvml.nvmlDeviceGetHandleByIndex(0)

                # Memory info
                memory_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                memory_used_mb = memory_info.used / (1024 * 1024)
                memory_total_mb = memory_info.total / (1024 * 1024)

                # Utilization
                utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)
                utilization_percent = utilization.gpu

                return {
                    'memory_used_mb': memory_used_mb,
                    'memory_total_mb': memory_total_mb,
                    'utilization_percent': utilization_percent
                }
        except:
            pass  # NVIDIA GPU not available or pynvml not installed

        # Could add support for AMD GPUs here
        return None

    async def _check_performance_warnings(self, metrics: SystemMetrics):
        """Check for performance issues and log warnings."""
        if metrics.cpu_percent > self.cpu_warning_threshold:
            logger.warning(f"High CPU usage: {metrics.cpu_percent:.1f}%")

        if metrics.memory_percent > self.memory_warning_threshold:
            logger.warning(f"High memory usage: {metrics.memory_percent:.1f}%")

        if (metrics.gpu_memory_used_mb and metrics.gpu_memory_total_mb and
                (metrics.gpu_memory_used_mb / metrics.gpu_memory_total_mb * 100) > self.gpu_memory_warning_threshold):
            logger.warning(
                f"High GPU memory usage: {metrics.gpu_memory_used_mb:.0f}MB / {metrics.gpu_memory_total_mb:.0f}MB")

    def get_recent_metrics(self, minutes: int = 60) -> List[SystemMetrics]:
        """Get metrics from the last N minutes."""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        return [m for m in self.metrics_history if m.timestamp >= cutoff_time]

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of performance metrics."""
        if not self.metrics_history:
            return {}

        recent_metrics = self.get_recent_metrics(60)  # Last hour

        if not recent_metrics:
            return {}

        cpu_values = [m.cpu_percent for m in recent_metrics]
        memory_values = [m.memory_percent for m in recent_metrics]

        return {
            'monitoring_active': self.monitoring_active,
            'metrics_count': len(self.metrics_history),
            'last_hour': {
                'cpu_avg': sum(cpu_values) / len(cpu_values),
                'cpu_max': max(cpu_values),
                'memory_avg': sum(memory_values) / len(memory_values),
                'memory_max': max(memory_values),
                'sample_count': len(recent_metrics)
            }
        }


class ModelDownloadManager:
    """Manages downloading and installing models."""

    def __init__(self):
        self.models_dir = settings.models_dir
        self.download_progress: Dict[str, Dict[str, Any]] = {}

        # Model repository (could be external in production)
        self.model_repository = self._get_model_repository()

        logger.info("ModelDownloadManager initialized")

    def _get_model_repository(self) -> Dict[str, ModelDownloadInfo]:
        """Get available models for download."""
        # In production, this would fetch from a remote repository
        return {
            "phi-3.5-mini": ModelDownloadInfo(
                name="phi-3.5-mini",
                display_name="Phi-3.5 Mini (3.8B)",
                size_gb=2.3,
                download_url="https://huggingface.co/microsoft/Phi-3.5-mini-instruct-gguf/resolve/main/Phi-3.5-mini-instruct-q4_k_m.gguf",
                checksum="a1b2c3d4e5f6",  # Would be real checksum
                description="Fast and efficient 3.8B parameter model optimized for coding tasks",
                requirements={
                    "min_ram_gb": 8,
                    "recommended_ram_gb": 12,
                    "gpu_recommended": False
                },
                tags=["small", "fast", "code", "chat"]
            ),
            "qwen2.5-coder-7b": ModelDownloadInfo(
                name="qwen2.5-coder-7b",
                display_name="Qwen2.5-Coder (7B)",
                size_gb=4.2,
                download_url="https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct-GGUF/resolve/main/qwen2.5-coder-7b-instruct-q4_k_m.gguf",
                checksum="f1e2d3c4b5a6",
                description="Specialized 7B model for code generation and programming assistance",
                requirements={
                    "min_ram_gb": 16,
                    "recommended_ram_gb": 24,
                    "gpu_recommended": True
                },
                tags=["medium", "code", "balanced", "popular"]
            ),
            "deepseek-coder-33b": ModelDownloadInfo(
                name="deepseek-coder-33b",
                display_name="DeepSeek-Coder (33B)",
                size_gb=20.5,
                download_url="https://huggingface.co/deepseek-ai/deepseek-coder-33b-instruct-gguf/resolve/main/deepseek-coder-33b-instruct-q4_k_m.gguf",
                checksum="z9y8x7w6v5u4",
                description="Powerful 33B model for complex coding tasks and advanced problem solving",
                requirements={
                    "min_ram_gb": 32,
                    "recommended_ram_gb": 48,
                    "gpu_recommended": True
                },
                tags=["large", "powerful", "advanced", "gpu"]
            )
        }

    def list_available_models(self) -> List[Dict[str, Any]]:
        """List all available models for download."""
        models = []
        system_info = get_system_info()

        for model_info in self.model_repository.values():
            model_path = self.models_dir / get_model_config(model_info.name)["model_file"]

            models.append({
                **model_info.to_dict(),
                'installed': model_path.exists(),
                'installing': model_info.name in self.download_progress,
                'compatible': system_info["ram_gb"] >= model_info.requirements["min_ram_gb"],
                'download_progress': self.download_progress.get(model_info.name, {})
            })

        return models

    async def download_model(self, model_name: str) -> AsyncIterator[Dict[str, Any]]:
        """Download a model with progress updates."""
        if model_name not in self.model_repository:
            raise ValueError(f"Model {model_name} not found in repository")

        model_info = self.model_repository[model_name]
        model_config = get_model_config(model_name)
        output_path = self.models_dir / model_config["model_file"]

        # Check if already installed
        if output_path.exists():
            yield {"status": "already_installed", "message": "Model already exists"}
            return

        # Check system requirements
        system_info = get_system_info()
        if system_info["ram_gb"] < model_info.requirements["min_ram_gb"]:
            raise ValueError(
                f"Insufficient RAM: {system_info['ram_gb']}GB < {model_info.requirements['min_ram_gb']}GB required")

        # Initialize progress tracking
        self.download_progress[model_name] = {
            "status": "starting",
            "downloaded_bytes": 0,
            "total_bytes": 0,
            "progress_percent": 0,
            "speed_mbps": 0,
            "eta_seconds": 0
        }

        try:
            start_time = time.time()

            async with aiohttp.ClientSession() as session:
                logger.info(f"Starting download of {model_name} from {model_info.download_url}")

                async with session.get(model_info.download_url) as response:
                    if response.status != 200:
                        raise Exception(f"Download failed: HTTP {response.status}")

                    total_size = int(response.headers.get('content-length', 0))
                    self.download_progress[model_name]["total_bytes"] = total_size
                    self.download_progress[model_name]["status"] = "downloading"

                    downloaded = 0
                    chunk_size = 8192

                    async with aiofiles.open(output_path, 'wb') as f:
                        async for chunk in response.content.iter_chunked(chunk_size):
                            await f.write(chunk)
                            downloaded += len(chunk)

                            # Update progress
                            elapsed = time.time() - start_time
                            progress_percent = (downloaded / total_size * 100) if total_size > 0 else 0
                            speed_mbps = (downloaded / (1024 * 1024)) / elapsed if elapsed > 0 else 0
                            eta_seconds = ((total_size - downloaded) / (
                                        downloaded / elapsed)) if downloaded > 0 and elapsed > 0 else 0

                            self.download_progress[model_name].update({
                                "downloaded_bytes": downloaded,
                                "progress_percent": progress_percent,
                                "speed_mbps": speed_mbps,
                                "eta_seconds": eta_seconds
                            })

                            # Yield progress update every 1MB
                            if downloaded % (1024 * 1024) == 0 or downloaded == total_size:
                                yield {
                                    "status": "downloading",
                                    "progress": self.download_progress[model_name]
                                }

            # Verify download
            await self._verify_download(output_path, model_info.checksum)

            self.download_progress[model_name]["status"] = "completed"
            yield {
                "status": "completed",
                "message": f"Model {model_name} downloaded successfully",
                "path": str(output_path)
            }

            logger.info(f"Model {model_name} downloaded successfully to {output_path}")

        except Exception as e:
            self.download_progress[model_name]["status"] = "failed"

            # Clean up partial download
            if output_path.exists():
                output_path.unlink()

            logger.error(f"Model download failed: {e}")
            yield {"status": "failed", "error": str(e)}

        finally:
            # Clean up progress tracking after a delay
            asyncio.create_task(self._cleanup_progress(model_name))

    async def _verify_download(self, file_path: Path, expected_checksum: str):
        """Verify downloaded file integrity."""
        # For now, just check file exists and has reasonable size
        # In production, would verify actual checksum
        if not file_path.exists():
            raise Exception("Downloaded file does not exist")

        file_size = file_path.stat().st_size
        if file_size < 1024 * 1024:  # Less than 1MB
            raise Exception("Downloaded file is too small")

        logger.info(f"Download verification passed for {file_path.name}")

    async def _cleanup_progress(self, model_name: str):
        """Clean up progress tracking after delay."""
        await asyncio.sleep(300)  # Wait 5 minutes
        if model_name in self.download_progress:
            del self.download_progress[model_name]

    def get_download_status(self, model_name: str) -> Dict[str, Any]:
        """Get download status for a model."""
        return self.download_progress.get(model_name, {"status": "not_started"})

    def cancel_download(self, model_name: str) -> bool:
        """Cancel an ongoing download."""
        if model_name in self.download_progress:
            self.download_progress[model_name]["status"] = "cancelled"
            # In a real implementation, would cancel the actual download task
            return True
        return False


class SystemDiagnostics:
    """System diagnostics and health checks."""

    def __init__(self):
        self.performance_monitor = PerformanceMonitor()
        self.model_download_manager = ModelDownloadManager()

    async def run_health_check(self) -> Dict[str, Any]:
        """Run comprehensive system health check."""
        checks = {}

        # System info
        system_info = get_system_info()
        checks["system_info"] = {
            "status": "ok",
            "details": system_info
        }

        # Memory check
        memory = psutil.virtual_memory()
        memory_status = "ok" if memory.percent < 90 else "warning" if memory.percent < 95 else "critical"
        checks["memory"] = {
            "status": memory_status,
            "details": {
                "usage_percent": memory.percent,
                "available_gb": memory.available / (1024 ** 3),
                "total_gb": memory.total / (1024 ** 3)
            }
        }

        # Disk space check
        disk = psutil.disk_usage('/')
        disk_usage_percent = (disk.used / disk.total) * 100
        disk_status = "ok" if disk_usage_percent < 85 else "warning" if disk_usage_percent < 95 else "critical"
        checks["disk_space"] = {
            "status": disk_status,
            "details": {
                "usage_percent": disk_usage_percent,
                "free_gb": disk.free / (1024 ** 3),
                "total_gb": disk.total / (1024 ** 3)
            }
        }

        # Models directory check
        models_dir_exists = settings.models_dir.exists()
        models_dir_writable = os.access(str(settings.models_dir), os.W_OK) if models_dir_exists else False
        checks["models_directory"] = {
            "status": "ok" if models_dir_exists and models_dir_writable else "error",
            "details": {
                "path": str(settings.models_dir),
                "exists": models_dir_exists,
                "writable": models_dir_writable
            }
        }

        # Database check
        db_path = Path(settings.database_url)
        db_dir_exists = db_path.parent.exists()
        db_dir_writable = os.access(str(db_path.parent), os.W_OK) if db_dir_exists else False
        checks["database"] = {
            "status": "ok" if db_dir_exists and db_dir_writable else "error",
            "details": {
                "path": str(db_path),
                "directory_exists": db_dir_exists,
                "directory_writable": db_dir_writable
            }
        }

        # Dependencies check
        checks["dependencies"] = await self._check_dependencies()

        # Overall status
        statuses = [check["status"] for check in checks.values()]
        if "critical" in statuses or "error" in statuses:
            overall_status = "error"
        elif "warning" in statuses:
            overall_status = "warning"
        else:
            overall_status = "ok"

        return {
            "overall_status": overall_status,
            "timestamp": datetime.now().isoformat(),
            "checks": checks
        }

    async def _check_dependencies(self) -> Dict[str, Any]:
        """Check for required dependencies."""
        dependencies = {
            "required": {},
            "optional": {}
        }

        # Required dependencies
        required_packages = [
            ("fastapi", "FastAPI web framework"),
            ("uvicorn", "ASGI server"),
            ("loguru", "Logging"),
            ("pydantic", "Data validation"),
            ("psutil", "System monitoring")
        ]

        for package, description in required_packages:
            try:
                __import__(package)
                dependencies["required"][package] = {"status": "ok", "description": description}
            except ImportError:
                dependencies["required"][package] = {"status": "missing", "description": description}

        # Optional dependencies
        optional_packages = [
            ("llama_cpp", "LLaMA inference"),
            ("sentence_transformers", "Text embeddings"),
            ("numpy", "Numerical computing"),
            ("aiohttp", "HTTP client"),
            ("aiofiles", "Async file operations"),
            ("cryptography", "Encryption"),
            ("pynvml", "NVIDIA GPU monitoring")
        ]

        for package, description in optional_packages:
            try:
                __import__(package)
                dependencies["optional"][package] = {"status": "ok", "description": description}
            except ImportError:
                dependencies["optional"][package] = {"status": "missing", "description": description}

        # Calculate status
        required_missing = [pkg for pkg, info in dependencies["required"].items() if info["status"] == "missing"]
        if required_missing:
            status = "error"
        else:
            status = "ok"

        return {
            "status": status,
            "details": dependencies,
            "missing_required": required_missing
        }

    def get_system_summary(self) -> Dict[str, Any]:
        """Get comprehensive system summary."""
        system_info = get_system_info()
        metrics_summary = self.performance_monitor.get_metrics_summary()

        return {
            "system": system_info,
            "performance": metrics_summary,
            "models": {
                "directory": str(settings.models_dir),
                "available_for_download": len(self.model_download_manager.model_repository)
            },
            "services": {
                "performance_monitoring": self.performance_monitor.monitoring_active
            }
        }