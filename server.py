"""helix-sandbox — Secure sandbox MCP server for AI agents"""

import base64
import logging
import sys
from pathlib import Path

from fastmcp import FastMCP

# Ensure project root is importable
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

logger = logging.getLogger(__name__)

mcp = FastMCP("helix-sandbox")

# Lazy singleton
_backend = None


def _get_backend():
    """Get or create the sandbox backend (lazy singleton)."""
    global _backend
    if _backend is None:
        from src.sandbox import BackendFactory
        _backend = BackendFactory.auto_select()
    return _backend


# ---------------------------------------------------------------------------
# MCP Tools
# ---------------------------------------------------------------------------


@mcp.tool()
def create_sandbox(
    backend: str = "auto",
    workspace_path: str = "",
    timeout_minutes: int = 30,
) -> dict:
    """Create a new sandbox environment.

    Args:
        backend: Backend type — "auto", "docker", or "windows_sandbox".
        workspace_path: Host path to mount as /workspace inside the sandbox.
        timeout_minutes: Auto-destroy timeout in minutes (0 = no timeout).

    Returns:
        dict with sandbox_id, backend_type, status, vnc_url, and workspace_path.
    """
    global _backend

    try:
        if backend != "auto" or _backend is None:
            from src.sandbox import BackendFactory
            _backend = BackendFactory.create(backend)

        if _backend is None:
            return {"ok": False, "error": "No sandbox backend available. Install Docker or enable Windows Sandbox."}

        if not _backend.is_available():
            reason = _backend.get_unavailable_reason()
            return {"ok": False, "error": f"Backend not available: {reason}"}

        from src.sandbox import SandboxConfig
        config = SandboxConfig(
            workspace_path=workspace_path,
            timeout_minutes=timeout_minutes,
        )

        info = _backend.create(config)
        if info is None:
            return {"ok": False, "error": "Failed to create sandbox"}

        return {
            "ok": True,
            "sandbox_id": info.sandbox_id,
            "backend_type": _backend.backend_type(),
            "status": info.status.value,
            "vnc_url": info.vnc_url,
            "workspace_path": info.workspace_path,
        }
    except Exception as e:
        logger.error(f"create_sandbox failed: {e}")
        return {"ok": False, "error": str(e)}


@mcp.tool()
def destroy_sandbox() -> dict:
    """Destroy the current sandbox environment.

    Returns:
        dict with ok status.
    """
    backend = _get_backend()
    if backend is None:
        return {"ok": False, "error": "No sandbox is running"}

    try:
        result = backend.destroy()
        return {"ok": result}
    except Exception as e:
        logger.error(f"destroy_sandbox failed: {e}")
        return {"ok": False, "error": str(e)}


@mcp.tool()
def sandbox_status() -> dict:
    """Get the current sandbox status.

    Returns:
        dict with status, backend_type, and availability info.
    """
    backend = _get_backend()
    if backend is None:
        return {
            "status": "none",
            "backend_type": "none",
            "available": False,
            "reason": "No sandbox backend available",
        }

    try:
        status = backend.get_status()
        return {
            "status": status.value,
            "backend_type": backend.backend_type(),
            "available": backend.is_available(),
            "vnc_url": backend.get_vnc_url(),
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@mcp.tool()
def execute_command(command: str, workdir: str = "/workspace") -> dict:
    """Execute a command inside the sandbox.

    Args:
        command: Shell command to execute.
        workdir: Working directory inside the sandbox.

    Returns:
        dict with exit_code, stdout, and stderr.
    """
    backend = _get_backend()
    if backend is None:
        return {"exit_code": -1, "stdout": "", "stderr": "No sandbox is running"}

    try:
        result = backend.exec_in_sandbox(command)
        if result is not None:
            return {"exit_code": 0, "stdout": result, "stderr": ""}

        # Fall back to manager's execute if backend is DockerBackend
        if hasattr(backend, 'manager'):
            return backend.manager.execute(command, workdir=workdir)

        return {"exit_code": -1, "stdout": "", "stderr": "Command execution not supported by this backend"}
    except Exception as e:
        return {"exit_code": -1, "stdout": "", "stderr": str(e)}


@mcp.tool()
def read_file(path: str) -> dict:
    """Read a file from inside the sandbox.

    Args:
        path: File path inside the sandbox (e.g. "/workspace/main.py").

    Returns:
        dict with content or error.
    """
    backend = _get_backend()
    if backend is None:
        return {"error": "No sandbox is running"}

    try:
        # DockerBackend.read_file returns bytes, SandboxManager.read_file returns dict
        raw = backend.read_file(path)
        if isinstance(raw, bytes):
            if not raw:
                return {"error": "File not found or empty"}
            return {"content": raw.decode("utf-8", errors="replace"), "path": path}
        elif isinstance(raw, dict):
            return raw
        return {"error": "Unexpected return type from read_file"}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def write_file(path: str, content: str) -> dict:
    """Write a file inside the sandbox.

    Args:
        path: File path inside the sandbox (e.g. "/workspace/main.py").
        content: File content to write.

    Returns:
        dict with success status or error.
    """
    backend = _get_backend()
    if backend is None:
        return {"error": "No sandbox is running"}

    try:
        if hasattr(backend, 'manager'):
            return backend.manager.write_file(path, content)
        return {"error": "Write not supported by this backend"}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def list_directory(path: str = "/workspace") -> dict:
    """List directory contents inside the sandbox.

    Args:
        path: Directory path inside the sandbox.

    Returns:
        dict with path and entries list, or error.
    """
    backend = _get_backend()
    if backend is None:
        return {"error": "No sandbox is running"}

    try:
        entries = backend.list_files(path)
        return {"ok": True, "path": path, "entries": entries}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def screenshot() -> dict:
    """Capture a screenshot from inside the sandbox.

    Returns:
        dict with base64-encoded PNG image data, or error.
    """
    backend = _get_backend()
    if backend is None:
        return {"error": "No sandbox is running"}

    try:
        png_bytes = backend.screenshot()
        if png_bytes is None:
            return {"error": "Screenshot not available (backend may not support it)"}

        b64 = base64.b64encode(png_bytes).decode("ascii")
        return {
            "ok": True,
            "format": "png",
            "base64": b64,
            "size_bytes": len(png_bytes),
        }
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def get_diff() -> dict:
    """Get the change diff from the sandbox workspace.

    Returns:
        dict with unified diff string, or error.
    """
    backend = _get_backend()
    if backend is None:
        return {"error": "No sandbox is running"}

    try:
        diff = backend.get_diff()
        return {"ok": True, "diff": diff}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def container_stats() -> dict:
    """Get resource usage statistics for the sandbox container.

    Returns:
        dict with cpu_percent, memory_mb, memory_limit_mb, or error.
    """
    backend = _get_backend()
    if backend is None:
        return {"error": "No sandbox is running"}

    try:
        stats = backend.get_container_stats()
        if stats is None:
            return {"error": "Stats not available (backend may not support it)"}
        stats["ok"] = True
        return stats
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    mcp.run()
