"""helix-sandbox — Docker backend (optional / adapter)

Backend for Docker-compatible runtimes (Docker Desktop / Rancher Desktop).
Wraps the existing SandboxManager to conform to the SandboxBackend interface.
"""

import logging
from typing import Optional

from .backend_base import BackendCapability, SandboxBackend
from .sandbox_config import SandboxInfo, SandboxStatus
from .sandbox_manager import SandboxManager

logger = logging.getLogger(__name__)


class DockerBackend(SandboxBackend):
    """SandboxManager wrapper — conforms to SandboxBackend interface

    Optional backend for Docker-compatible runtimes (Docker Desktop / Rancher Desktop).
    Provides all capabilities: embed view, file browsing, command execution,
    screenshot, promotion, resource stats, and network configuration.
    """

    def __init__(self):
        super().__init__()
        self._manager = SandboxManager()

        # Forward SandboxManager signals
        self._manager.statusChanged.connect(lambda *a: self.statusChanged.emit(*a))
        self._manager.errorOccurred.connect(lambda *a: self.errorOccurred.emit(*a))
        self._manager.outputReceived.connect(lambda *a: self.outputReceived.emit(*a))

    @property
    def manager(self) -> SandboxManager:
        """Direct reference to internal SandboxManager (for compatibility)"""
        return self._manager

    # --- Required methods ---

    def backend_type(self) -> str:
        return "docker"

    def capabilities(self) -> BackendCapability:
        return (
            BackendCapability.EMBED_VIEW
            | BackendCapability.FILE_BROWSE
            | BackendCapability.EXEC_COMMAND
            | BackendCapability.SCREENSHOT
            | BackendCapability.DIFF_PROMOTE
            | BackendCapability.STATS
            | BackendCapability.NETWORKING
        )

    def is_available(self) -> bool:
        return self._manager.is_docker_available()

    def get_unavailable_reason(self) -> str:
        return self._manager.get_docker_unavailable_reason()

    def create(self, config) -> Optional[SandboxInfo]:
        return self._manager.create(config)

    def destroy(self) -> bool:
        return self._manager.destroy()

    def get_status(self) -> SandboxStatus:
        return self._manager.get_status()

    # --- Optional methods (delegated to SandboxManager) ---

    def get_diff(self) -> str:
        return self._manager.get_diff()

    def screenshot(self) -> Optional[bytes]:
        return self._manager.screenshot()

    def list_files(self, path: str = "/workspace") -> list:
        result = self._manager.list_dir(path)
        if result.get("ok") and "entries" in result:
            return result["entries"]
        return []

    def read_file(self, path: str) -> dict | bytes:
        return self._manager.read_file(path)

    def get_container_stats(self) -> Optional[dict]:
        return self._manager.get_container_stats()

    def get_vnc_url(self) -> str:
        url = self._manager.get_vnc_url()
        return url or ""

    def reset_connection(self):
        self._manager.reset_connection()

    # --- Docker-specific methods ---

    def check_image_exists(self) -> bool:
        return self._manager.check_image_exists()

    def build_image(self, progress_callback=None) -> bool:
        return self._manager.build_image(progress_callback)

    def remove_image(self, force: bool = True) -> bool:
        return self._manager.remove_image(force)

    def exec_in_sandbox(self, command: str) -> Optional[str]:
        result = self._manager.execute(command)
        if result.get("exit_code") == 0:
            return result.get("stdout", "")
        return None

    def get_workspace_path(self) -> str:
        info = self._manager.get_info()
        if info:
            return info.workspace_path
        return ""
