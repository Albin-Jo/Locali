import sys
from pathlib import Path

from loguru import logger

from .config import settings


def setup_logging():
    """Configure loguru logging for the application."""

    # Remove default handler
    logger.remove()

    # Console handler with nice formatting
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
               "<level>{message}</level>",
        level=settings.log_level,
        colorize=True,
        backtrace=True,
        diagnose=True
    )

    # File handler if log file is specified
    if settings.log_file:
        log_path = Path(settings.log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        logger.add(
            str(log_path),
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | "
                   "{name}:{function}:{line} | {message}",
            level=settings.log_level,
            rotation="10 MB",
            retention="1 week",
            compression="zip",
            backtrace=True,
            diagnose=True
        )

    # Performance logging for slow operations
    logger.add(
        "logs/performance.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
        level="INFO",
        filter=lambda record: "performance" in record["extra"],
        rotation="1 day",
        retention="1 week"
    )

    # Model operations logging
    logger.add(
        "logs/models.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
        level="DEBUG",
        filter=lambda record: "model" in record["extra"],
        rotation="1 day",
        retention="3 days"
    )

    logger.info(f"Logging configured - Level: {settings.log_level}")


def get_logger(name: str):
    """Get a logger instance for a specific module."""
    return logger.bind(name=name)


def log_performance(operation: str):
    """Decorator to log performance of operations."""

    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            import time
            start_time = time.perf_counter()

            try:
                result = await func(*args, **kwargs)
                elapsed = time.perf_counter() - start_time

                logger.bind(performance=True).info(
                    f"{operation} completed in {elapsed:.3f}s"
                )

                # Warn if operation is slow
                if elapsed > 3.0:
                    logger.bind(performance=True).warning(
                        f"Slow operation: {operation} took {elapsed:.3f}s"
                    )

                return result

            except Exception as e:
                elapsed = time.perf_counter() - start_time
                logger.bind(performance=True).error(
                    f"{operation} failed after {elapsed:.3f}s: {e}"
                )
                raise

        def sync_wrapper(*args, **kwargs):
            import time
            start_time = time.perf_counter()

            try:
                result = func(*args, **kwargs)
                elapsed = time.perf_counter() - start_time

                logger.bind(performance=True).info(
                    f"{operation} completed in {elapsed:.3f}s"
                )

                if elapsed > 3.0:
                    logger.bind(performance=True).warning(
                        f"Slow operation: {operation} took {elapsed:.3f}s"
                    )

                return result

            except Exception as e:
                elapsed = time.perf_counter() - start_time
                logger.bind(performance=True).error(
                    f"{operation} failed after {elapsed:.3f}s: {e}"
                )
                raise

        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def log_model_operation(operation: str, model_name: str = None):
    """Log model-specific operations."""

    def log_func(message: str, level: str = "info"):
        model_info = f"[{model_name}] " if model_name else ""
        full_message = f"{operation}: {model_info}{message}"

        getattr(logger.bind(model=True), level)(full_message)

    return log_func
