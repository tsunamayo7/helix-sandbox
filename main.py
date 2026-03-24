"""helix-sandbox — Entry point

Supports both MCP server mode and CLI mode.

Usage:
    python main.py          # Start MCP server (stdio transport)
    python main.py --info   # Show backend availability info
"""

import sys
from pathlib import Path

# Ensure project root is importable
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def show_info():
    """Display backend availability information."""
    from src.sandbox import BackendFactory

    print("helix-sandbox v2.0.0")
    print("=" * 40)

    # Check Windows Sandbox
    try:
        from src.sandbox.windows_sandbox_backend import WindowsSandboxBackend
        wsb = WindowsSandboxBackend()
        if wsb.is_available():
            print("[OK] Windows Sandbox: available")
        else:
            print(f"[--] Windows Sandbox: {wsb.get_unavailable_reason()}")
    except Exception as e:
        print(f"[--] Windows Sandbox: check failed ({e})")

    # Check Docker
    try:
        from src.sandbox.docker_backend import DockerBackend
        docker = DockerBackend()
        if docker.is_available():
            print("[OK] Docker: available")
        else:
            print(f"[--] Docker: {docker.get_unavailable_reason()}")
    except Exception as e:
        print(f"[--] Docker: check failed ({e})")

    # Auto-select
    backend = BackendFactory.auto_select()
    if backend:
        print(f"\nAuto-selected backend: {backend.backend_type()}")
    else:
        print("\nNo backend available.")


def main():
    if "--info" in sys.argv:
        show_info()
        return

    # Start MCP server
    from server import mcp
    mcp.run()


if __name__ == "__main__":
    main()
