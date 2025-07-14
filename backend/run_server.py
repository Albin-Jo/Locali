# backend/run_server.py
"""
Startup script for the Locali backend with Python 3.13 compatibility fixes.
"""

import asyncio
import os
import sys
import socket
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.core.config import settings
from loguru import logger


def check_port_availability(host: str, port: int) -> bool:
    """Check if port is available."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            return result != 0  # Port is available if connection fails
    except Exception:
        return False


def find_available_port(host: str, start_port: int, max_attempts: int = 10) -> int:
    """Find an available port starting from start_port."""
    for port in range(start_port, start_port + max_attempts):
        if check_port_availability(host, port):
            return port

    raise RuntimeError(f"No available port found in range {start_port}-{start_port + max_attempts}")


def setup_python_313_compatibility():
    """Setup compatibility fixes for Python 3.13."""
    if sys.version_info >= (3, 13):
        logger.info("Applying Python 3.13 compatibility fixes...")

        # Set event loop policy for Windows
        if sys.platform == 'win32':
            # Use SelectorEventLoop instead of ProactorEventLoop for better compatibility
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
            logger.info("Set Windows Selector Event Loop Policy for Python 3.13")


def main():
    """Main startup function."""
    print("🚀 Starting Locali Backend Server...")

    # Setup Python 3.13 compatibility
    setup_python_313_compatibility()

    # Check if port is available
    host = settings.host
    port = settings.port

    if not check_port_availability(host, port):
        logger.warning(f"Port {port} is already in use")
        try:
            port = find_available_port(host, port + 1)
            logger.info(f"Using alternative port: {port}")
        except RuntimeError as e:
            logger.error(f"Cannot find available port: {e}")
            print(f"❌ Error: Port {settings.port} is already in use and no alternative found.")
            print("Please check if another instance is running or change LOCALI_PORT in .env file")
            sys.exit(1)

    # Create required directories
    required_dirs = [
        settings.models_dir,
        Path(settings.database_url).parent,
        Path(settings.vector_db_path),
        Path("logs")
    ]

    for dir_path in required_dirs:
        dir_path.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Ensured directory exists: {dir_path}")

    # Set environment variables for better compatibility
    os.environ.setdefault('PYTHONPATH', str(backend_dir))

    # Import and run uvicorn with proper settings
    try:
        import uvicorn

        # Configure uvicorn for Python 3.13 compatibility
        uvicorn_config = {
            "app": "backend.app.main:app",
            "host": host,
            "port": port,
            "reload": settings.reload and settings.debug,
            "log_level": settings.log_level.lower(),
            "access_log": settings.debug,
            "workers": 1,  # Single worker for development
        }

        # Use different loop implementations based on platform and Python version
        if sys.platform == 'win32' and sys.version_info >= (3, 13):
            uvicorn_config["loop"] = "asyncio"  # Force asyncio loop

        logger.info(f"Starting server at http://{host}:{port}")
        logger.info(f"Debug mode: {settings.debug}")
        logger.info(f"Reload enabled: {settings.reload and settings.debug}")

        # Run the server
        uvicorn.run(**uvicorn_config)

    except ImportError:
        logger.error("uvicorn is not installed. Please install it with: pip install uvicorn[standard]")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("🛑 Server stopped by user")
    except Exception as e:
        logger.error(f"❌ Server startup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()