"""helix-sandbox — Sandbox package

Backend collection for sandbox environments.
BackendFactory auto-selects: Windows Sandbox (built-in) -> Docker (optional).
"""

from .sandbox_config import SandboxConfig, SandboxInfo, SandboxStatus, WindowsSandboxConfig
from .backend_base import BackendCapability, SandboxBackend
from .backend_factory import BackendFactory

__all__ = [
    "SandboxConfig", "SandboxInfo", "SandboxStatus", "WindowsSandboxConfig",
    "BackendCapability", "SandboxBackend", "BackendFactory",
]
