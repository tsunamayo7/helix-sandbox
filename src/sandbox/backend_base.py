"""helix-sandbox — Sandbox backend abstract base class

Common interface for all backends (Windows Sandbox / Docker / Guacamole).
BackendCapability flags declare backend-specific features,
allowing the server to adapt behavior dynamically.
"""

import logging
from abc import abstractmethod
from enum import Flag, auto
from typing import Optional

from .sandbox_config import SandboxInfo, SandboxStatus

logger = logging.getLogger(__name__)


class _Signal:
    """Simple callback-based signal replacement for PyQt6 signals."""

    def __init__(self):
        self._callbacks = []

    def connect(self, callback):
        self._callbacks.append(callback)

    def emit(self, *args):
        for cb in self._callbacks:
            try:
                cb(*args)
            except Exception:
                pass


class BackendCapability(Flag):
    """Feature flags provided by a backend"""
    NONE          = 0
    EMBED_VIEW    = auto()   # In-app NoVNC/WebView embedding
    FILE_BROWSE   = auto()   # File browsing inside container
    EXEC_COMMAND  = auto()   # Command execution inside container
    SCREENSHOT    = auto()   # Screenshot capture
    DIFF_PROMOTE  = auto()   # Diff detection + promotion
    STATS         = auto()   # CPU/RAM resource statistics
    NETWORKING    = auto()   # Network mode configuration


class SandboxBackend:
    """Abstract base class for sandbox backends

    All backends inherit this class and implement:
    backend_type / capabilities / is_available / create / destroy / get_status.
    Optional features are overridden based on capabilities().
    """

    def __init__(self):
        self.statusChanged = _Signal()
        self.outputReceived = _Signal()
        self.errorOccurred = _Signal()

    # --- Required methods ---

    @abstractmethod
    def backend_type(self) -> str:
        """Return backend identifier (e.g. "windows_sandbox", "docker")"""
        ...

    @abstractmethod
    def capabilities(self) -> BackendCapability:
        """Return feature flags provided by this backend"""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the backend is available"""
        ...

    @abstractmethod
    def get_unavailable_reason(self) -> str:
        """Return human-readable reason when unavailable"""
        ...

    @abstractmethod
    def create(self, config) -> Optional[SandboxInfo]:
        """Create and start a sandbox"""
        ...

    @abstractmethod
    def destroy(self) -> bool:
        """Stop and destroy the sandbox"""
        ...

    @abstractmethod
    def get_status(self) -> SandboxStatus:
        """Return current sandbox status"""
        ...

    # --- Optional methods (override based on capability) ---

    def get_diff(self) -> str:
        """Get changes in unified diff format (DIFF_PROMOTE)"""
        return ""

    def screenshot(self) -> Optional[bytes]:
        """Return screenshot as PNG bytes (SCREENSHOT)"""
        return None

    def list_files(self, path: str = "/workspace") -> list:
        """List files at the specified path (FILE_BROWSE)"""
        return []

    def read_file(self, path: str) -> bytes:
        """Read file content at the specified path (FILE_BROWSE)"""
        return b""

    def get_container_stats(self) -> Optional[dict]:
        """Return CPU/RAM statistics as dict (STATS)"""
        return None

    def get_vnc_url(self) -> str:
        """Return NoVNC / remote desktop URL (EMBED_VIEW)"""
        return ""

    def reset_connection(self):
        """Reset cached connection (for reconnection)"""
        pass

    # --- Docker-compatible methods (backward compatibility) ---

    def check_image_exists(self) -> bool:
        """Check if Docker image exists (Docker backend only)"""
        return False

    def build_image(self, progress_callback=None) -> bool:
        """Build Docker image (Docker backend only)"""
        return False

    def remove_image(self, force: bool = True) -> bool:
        """Remove Docker image (Docker backend only)"""
        return False

    def exec_in_sandbox(self, command: str) -> Optional[str]:
        """Execute command inside sandbox (EXEC_COMMAND)"""
        return None

    def get_workspace_path(self) -> str:
        """Return host-side workspace path"""
        return ""
