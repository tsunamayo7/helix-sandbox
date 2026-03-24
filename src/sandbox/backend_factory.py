"""helix-sandbox — Backend factory

Auto mode: Windows Sandbox -> Docker -> None (in order of priority).
Manual: explicitly select "windows_sandbox" / "docker".
"""

import logging
from typing import Optional

from .backend_base import SandboxBackend

logger = logging.getLogger(__name__)


class BackendFactory:
    """Sandbox backend factory"""

    @staticmethod
    def auto_select() -> Optional[SandboxBackend]:
        """Auto-select an available backend

        Priority:
        1. Windows Sandbox (no additional runtime required)
        2. Docker (Docker Desktop / Rancher Desktop required)
        3. None (neither available)
        """
        # 1. Windows Sandbox
        try:
            from .windows_sandbox_backend import WindowsSandboxBackend
            wsb = WindowsSandboxBackend()
            if wsb.is_available():
                logger.info("[BackendFactory] Auto-selected: Windows Sandbox")
                return wsb
            logger.debug("[BackendFactory] Windows Sandbox not available, trying Docker...")
        except Exception as e:
            logger.debug(f"[BackendFactory] Windows Sandbox check failed: {e}")

        # 2. Docker
        try:
            from .docker_backend import DockerBackend
            docker = DockerBackend()
            if docker.is_available():
                logger.info("[BackendFactory] Auto-selected: Docker")
                return docker
            logger.debug("[BackendFactory] Docker not available")
        except Exception as e:
            logger.debug(f"[BackendFactory] Docker check failed: {e}")

        # 3. Neither available
        logger.warning("[BackendFactory] No sandbox backend available")
        return None

    @staticmethod
    def create(backend_type: str) -> Optional[SandboxBackend]:
        """Create a backend of the specified type

        Args:
            backend_type: "auto" / "windows_sandbox" / "docker"

        Returns:
            SandboxBackend instance, or None
        """
        if backend_type == "auto":
            return BackendFactory.auto_select()

        if backend_type == "windows_sandbox":
            from .windows_sandbox_backend import WindowsSandboxBackend
            backend = WindowsSandboxBackend()
            if backend.is_available():
                return backend
            logger.warning("[BackendFactory] Windows Sandbox requested but not available")
            return backend  # Return instance anyway (for displaying reason)

        if backend_type == "docker":
            from .docker_backend import DockerBackend
            backend = DockerBackend()
            return backend  # Docker has connection latency, check availability later

        logger.warning(f"[BackendFactory] Unknown backend type: {backend_type}")
        return None
