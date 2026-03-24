"""helix-sandbox — SandboxManager

Manages Docker container CRUD, file operations, and command execution.
Gracefully handles missing Docker installation without raising ImportError.
"""

import base64
import logging
import os
import socket
import threading
import time
from pathlib import Path
from typing import Optional, Callable

from .backend_base import _Signal
from .sandbox_config import SandboxConfig, SandboxInfo, SandboxStatus
from ..utils.subprocess_utils import run_hidden

logger = logging.getLogger(__name__)

# docker package is an optional dependency
try:
    import docker
    from docker.errors import DockerException, ImageNotFound, NotFound, APIError
    DOCKER_SDK_AVAILABLE = True
except ImportError:
    DOCKER_SDK_AVAILABLE = False
    logger.info("[SandboxManager] docker SDK not installed — sandbox features disabled")


def _find_free_port(start: int = 6080, end: int = 6180) -> int:
    """Find a free port in the given range."""
    for port in range(start, end):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                # Docker publishes to 0.0.0.0, so probing only 127.0.0.1 can
                # miss ports that are already allocated on other interfaces.
                s.bind(("0.0.0.0", port))
                return port
        except OSError:
            continue
    raise RuntimeError(f"No free port found in range {start}-{end}")


class SandboxManager:
    """Manages Docker container CRUD, file operations, and command execution"""

    def __init__(self):
        self.statusChanged = _Signal()
        self.outputReceived = _Signal()
        self.errorOccurred = _Signal()

        self._client = None
        self._active_sandbox: Optional[SandboxInfo] = None
        self._timeout_timer: Optional[threading.Timer] = None
        self._status = SandboxStatus.NONE

    # --- Docker connection ---

    def _get_client(self):
        """Lazy-initialize Docker client"""
        if not DOCKER_SDK_AVAILABLE:
            return None
        if self._client is None:
            try:
                self._client = docker.from_env()
                self._client.ping()
                logger.info("[SandboxManager] Docker connection established.")
            except Exception as e:
                logger.warning(
                    f"[SandboxManager] Docker connection failed: {e}\n"
                    "Docker Desktop / Rancher Desktop may not be running. "
                    "Start your container runtime and retry."
                )
                self._client = None
        return self._client

    def reset_connection(self):
        """Reset cached Docker client (for reconnection)"""
        self._client = None
        logger.debug("[SandboxManager] Client cache cleared (reset_connection).")

    @staticmethod
    def _is_docker_available_via_cli() -> bool:
        """CLI fallback: check if `docker version` succeeds"""
        try:
            result = run_hidden(
                ["docker", "version"],
                capture_output=True, timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False

    def get_docker_unavailable_reason(self) -> str:
        """Return human-readable reason why Docker is unavailable"""
        cli_ok = self._is_docker_available_via_cli()

        if not DOCKER_SDK_AVAILABLE:
            if cli_ok:
                return (
                    "docker CLI is available but the Python SDK is not installed.\n"
                    "Some features (image inspection/removal) work via CLI.\n"
                    "For full functionality: pip install docker"
                )
            return (
                "Docker is not available.\n"
                "Install and start Docker Desktop or Rancher Desktop.\n"
                "Python SDK is also required: pip install docker"
            )

        if not cli_ok:
            return (
                "docker CLI not found or Docker engine is not running.\n"
                "Start Docker Desktop or Rancher Desktop."
            )

        # CLI is OK but SDK connection fails (socket mismatch etc.)
        return (
            "docker CLI is available but Python SDK connection failed.\n"
            "Check the DOCKER_HOST environment variable.\n"
            "For Rancher Desktop, select the Moby/dockerd engine."
        )

    def is_docker_available(self) -> bool:
        """Check if Docker is available (SDK -> CLI two-stage fallback)"""
        # Stage 1: SDK check
        if DOCKER_SDK_AVAILABLE:
            try:
                client = self._get_client()
                if client:
                    client.ping()
                    return True
            except Exception:
                self.reset_connection()

        # Stage 2: CLI fallback
        if self._is_docker_available_via_cli():
            logger.info("[SandboxManager] Docker available via CLI fallback (SDK unavailable/failed).")
            return True

        return False

    def check_image_exists(self) -> bool:
        """Check if helix-sandbox:latest image exists (SDK -> CLI fallback)"""
        # Stage 1: SDK
        client = self._get_client()
        if client:
            try:
                client.images.get("helix-sandbox:latest")
                return True
            except Exception:
                return False

        # Stage 2: CLI fallback
        try:
            result = run_hidden(
                ["docker", "image", "inspect", "helix-sandbox:latest"],
                capture_output=True, timeout=10
            )
            return result.returncode == 0
        except Exception:
            return False

    def remove_image(self, force: bool = True) -> bool:
        """Remove helix-sandbox:latest image (SDK -> CLI fallback)"""
        # Stage 1: SDK
        client = self._get_client()
        if client:
            try:
                client.images.remove("helix-sandbox:latest", force=force)
                logger.info("[SandboxManager] Image removed via SDK")
                return True
            except Exception as e:
                logger.warning(f"[SandboxManager] SDK image removal failed: {e}")

        # Stage 2: CLI fallback
        try:
            args = ["docker", "rmi", "helix-sandbox:latest"]
            if force:
                args.insert(2, "--force")
            result = run_hidden(args, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                logger.info("[SandboxManager] Image removed via CLI fallback")
                return True
            logger.warning(f"[SandboxManager] CLI image removal failed: {result.stderr.strip()}")
        except Exception as e:
            logger.warning(f"[SandboxManager] CLI image removal error: {e}")

        self.errorOccurred.emit("Image removal failed (SDK/CLI both failed)")
        return False

    def build_image(self, progress_callback: Optional[Callable] = None) -> bool:
        """Build image from Dockerfile"""
        client = self._get_client()
        if not client:
            return False

        dockerfile_dir = Path(__file__).parent.parent.parent / "docker" / "sandbox"
        if not (dockerfile_dir / "Dockerfile").exists():
            self.errorOccurred.emit("Dockerfile not found")
            return False

        try:
            if progress_callback:
                progress_callback("Building sandbox image...")

            _image, logs = client.images.build(
                path=str(dockerfile_dir),
                tag="helix-sandbox:latest",
                rm=True,
            )
            for chunk in logs:
                if "stream" in chunk:
                    msg = chunk["stream"].strip()
                    if msg and progress_callback:
                        progress_callback(msg)

            logger.info("[SandboxManager] Image built: helix-sandbox:latest")
            return True
        except Exception as e:
            logger.error(f"[SandboxManager] Build failed: {e}")
            self.errorOccurred.emit(f"Build failed: {e}")
            return False

    # --- Container CRUD ---

    def create(self, config: SandboxConfig) -> Optional[SandboxInfo]:
        """Create and start a sandbox container"""
        client = self._get_client()
        if not client:
            self.errorOccurred.emit("Docker is not available")
            return None

        self._set_status(SandboxStatus.CREATING)

        try:
            # Port allocation
            novnc_port = _find_free_port(6080, 6180)
            vnc_port = _find_free_port(5900, 5999)

            container_name = f"helix-sandbox-{int(time.time())}"

            # Volume mount configuration
            volumes = {}
            if config.workspace_path and os.path.isdir(config.workspace_path):
                mode = "ro" if config.mount_readonly else "rw"
                volumes[os.path.abspath(config.workspace_path)] = {
                    "bind": "/workspace",
                    "mode": mode,
                }

            # Environment variables
            environment = {
                "DISPLAY": ":99",
                "RESOLUTION": f"{config.resolution}x24",
            }
            if config.vnc_password:
                environment["VNC_PASSWORD"] = config.vnc_password

            # CPU limit
            nano_cpus = int(config.cpu_limit * 1e9)

            # network_disabled=True disables port forwarding and prevents
            # NoVNC access, so use bridge mode at minimum
            effective_network = config.network_mode
            if effective_network == "none":
                effective_network = "bridge"

            # Allow container to access host services (e.g. Ollama localhost:11434)
            # via host.docker.internal
            extra_hosts = {"host.docker.internal": "host-gateway"}

            container = client.containers.run(
                image=config.image_name,
                detach=True,
                name=container_name,
                ports={"5900/tcp": vnc_port, "6080/tcp": novnc_port},
                environment=environment,
                volumes=volumes,
                nano_cpus=nano_cpus,
                mem_limit=config.memory_limit,
                network_mode=effective_network,
                extra_hosts=extra_hosts,
            )

            # Wait for container to start (max 10 seconds)
            for _ in range(20):
                container.reload()
                if container.status == "running":
                    break
                time.sleep(0.5)

            if container.status != "running":
                raise RuntimeError(f"Container failed to start: {container.status}")

            # Wait for NoVNC HTTP service to be ready (max 20 seconds)
            import urllib.request
            for i in range(40):
                try:
                    req = urllib.request.urlopen(
                        f"http://localhost:{novnc_port}/vnc.html", timeout=2
                    )
                    if req.status == 200:
                        logger.info(f"[SandboxManager] NoVNC HTTP ready after {(i+1)*0.5:.1f}s")
                        break
                except Exception:
                    time.sleep(0.5)
            else:
                logger.warning("[SandboxManager] NoVNC HTTP not ready after 20s, proceeding anyway")

            vnc_url = f"http://localhost:{novnc_port}/vnc.html"
            if config.vnc_password:
                vnc_url += f"?autoconnect=true&resize=scale&password={config.vnc_password}"
            else:
                vnc_url += "?autoconnect=true&resize=scale"

            info = SandboxInfo(
                sandbox_id=container.short_id,
                container_name=container_name,
                status=SandboxStatus.RUNNING,
                vnc_url=vnc_url,
                vnc_port=vnc_port,
                novnc_port=novnc_port,
                workspace_path=config.workspace_path,
                config=config,
            )

            self._active_sandbox = info
            self._set_status(SandboxStatus.RUNNING)

            # Timeout timer
            if config.timeout_minutes > 0:
                self._start_timeout(config.timeout_minutes)

            # Initialize workspace git for diff tracking
            try:
                self.execute("cd /workspace && git init && git add -A && git commit -m 'initial' --allow-empty 2>/dev/null", workdir="/workspace")
                logger.info("[SandboxManager] Workspace git initialized for diff tracking")
            except Exception as e:
                logger.debug(f"[SandboxManager] Workspace git init skipped: {e}")

            logger.info(f"[SandboxManager] Sandbox created: {container_name} (NoVNC: {novnc_port})")
            return info

        except Exception as e:
            logger.error(f"[SandboxManager] Create failed: {e}")
            # Clean up failed container
            try:
                client = self._get_client()
                if client:
                    c = client.containers.get(container_name)
                    c.remove(force=True)
                    logger.info(f"[SandboxManager] Cleaned up failed container: {container_name}")
            except Exception as cleanup_err:
                logger.debug(f"[SandboxManager] Failed to cleanup failed container '{container_name}': {cleanup_err}")
            self._set_status(SandboxStatus.ERROR)
            self.errorOccurred.emit(str(e))
            return None

    def execute(self, command: str, workdir: str = "/workspace") -> dict:
        """Execute command inside sandbox"""
        container = self._get_container()
        if not container:
            return {"exit_code": -1, "stdout": "", "stderr": "Sandbox not running"}

        try:
            result = container.exec_run(
                cmd=["bash", "-c", command],
                workdir=workdir,
                demux=True,
            )
            stdout = result.output[0].decode("utf-8", errors="replace") if result.output[0] else ""
            stderr = result.output[1].decode("utf-8", errors="replace") if result.output[1] else ""
            return {"exit_code": result.exit_code, "stdout": stdout, "stderr": stderr}
        except Exception as e:
            return {"exit_code": -1, "stdout": "", "stderr": str(e)}

    def write_file(self, path: str, content: str) -> dict:
        """Write a file inside the sandbox"""
        if not self._validate_sandbox_path(path):
            return {"error": "Invalid path: path traversal detected"}

        container = self._get_container()
        if not container:
            return {"error": "Sandbox not running"}

        try:
            # Base64 avoids shell quoting issues with newlines and quotes.
            encoded = base64.b64encode(content.encode("utf-8")).decode("ascii")
            cmd = (
                "python3 -c \"import base64, pathlib; "
                f"p=pathlib.Path({path!r}); "
                "p.parent.mkdir(parents=True, exist_ok=True); "
                f"p.write_text(base64.b64decode('{encoded}').decode('utf-8'), encoding='utf-8')\""
            )
            result = container.exec_run(cmd=["bash", "-c", cmd], workdir="/workspace")
            if result.exit_code == 0:
                return {"success": True, "path": path}
            else:
                output = result.output.decode("utf-8", errors="replace") if result.output else ""
                return {"error": f"Write failed: {output}"}
        except Exception as e:
            return {"error": str(e)}

    def read_file(self, path: str) -> dict:
        """Read a file inside the sandbox"""
        if not self._validate_sandbox_path(path):
            return {"error": "Invalid path: path traversal detected"}

        result = self.execute(f"cat '{path}'")
        if result["exit_code"] == 0:
            return {"content": result["stdout"], "path": path}
        return {"error": result["stderr"] or "File not found"}

    def list_dir(self, path: str = "/workspace") -> dict:
        """List directory contents inside sandbox (structured data)"""
        if not self._validate_sandbox_path(path):
            return {"error": "Invalid path: path traversal detected"}

        # Get JSON format: name, type(file/dir/link), size, permissions
        script = (
            f"python3 -c \""
            f"import os, json, stat; "
            f"p='{path}'; entries=[]; "
            f"[entries.append({{"
            f"'name':e,'type':'dir' if os.path.isdir(os.path.join(p,e)) else 'file',"
            f"'size':os.path.getsize(os.path.join(p,e)) if os.path.isfile(os.path.join(p,e)) else 0"
            f"}}) for e in sorted(os.listdir(p))]; "
            f"print(json.dumps({{'path':p,'entries':entries}}))\""
        )
        result = self.execute(script)
        if result["exit_code"] == 0:
            try:
                import json
                data = json.loads(result["stdout"].strip())
                data["ok"] = True
                return data
            except Exception as e:
                logger.debug(f"[SandboxManager] list_directory JSON parse fallback: {e}")
            # Fallback: raw text
            return {"ok": True, "listing": result["stdout"], "path": path}
        return {"error": result["stderr"] or "Directory not found"}

    def screenshot(self) -> Optional[bytes]:
        """Capture sandbox desktop screenshot (PNG) with GUI readiness wait."""
        container = self._get_container()
        if not container:
            return None

        # Multiple capture methods to maximize compatibility
        capture_commands = [
            # Method 1: xdotool + import (waits for active window)
            "xdotool search --onlyvisible --name '' >/dev/null 2>&1; "
            "import -window root -display :99 png:- 2>/dev/null",
            # Method 2: scrot (if available)
            "DISPLAY=:99 scrot -o /tmp/_screenshot.png 2>/dev/null && cat /tmp/_screenshot.png",
            # Method 3: xwd + convert
            "xwd -root -display :99 2>/dev/null | convert xwd:- png:- 2>/dev/null",
            # Method 4: plain import (fallback)
            "import -window root -display :99 png:- 2>/dev/null",
        ]

        for attempt in range(8):
            cmd = capture_commands[min(attempt, len(capture_commands) - 1)]
            try:
                result = container.exec_run(
                    cmd=["bash", "-c", cmd],
                    demux=True,
                )
                if result.exit_code == 0 and result.output[0]:
                    png_data = result.output[0]
                    # If image is too small, desktop may not be ready yet
                    if len(png_data) > 2048 or attempt >= 7:
                        return png_data
                    logger.debug(f"[SandboxManager] Screenshot too small ({len(png_data)}b), retrying ({attempt+1}/8)")
                    time.sleep(2)
            except Exception as e:
                logger.debug(f"[SandboxManager] Screenshot attempt {attempt+1} failed: {e}")
                time.sleep(2)
        return None

    def get_diff(self) -> str:
        """Get change diff inside sandbox"""
        container = self._get_container()
        if not container:
            return ""

        # Use git diff if git is initialized
        result = self.execute("cd /workspace && git add -A && git diff --cached --no-color 2>/dev/null || echo ''")
        diff_text = result.get("stdout", "").strip()
        if diff_text:
            return diff_text
        # Fallback
        result = self.execute("diff -rq /workspace /workspace-original 2>/dev/null || echo 'No diff available'")
        return result.get("stdout", "")

    def snapshot(self) -> Optional[str]:
        """Take a snapshot of current state (docker commit)"""
        container = self._get_container()
        if not container:
            return None

        try:
            tag = f"helix-sandbox-snapshot:{int(time.time())}"
            container.commit(repository="helix-sandbox-snapshot", tag=str(int(time.time())))
            return tag
        except Exception as e:
            logger.error(f"[SandboxManager] Snapshot failed: {e}")
            return None

    def destroy(self) -> bool:
        """Destroy sandbox container and volumes"""
        container = self._get_container()
        if not container:
            self._active_sandbox = None
            self._set_status(SandboxStatus.NONE)
            return True

        try:
            container.stop(timeout=5)
            container.remove(v=True)
            logger.info(f"[SandboxManager] Sandbox destroyed: {self._active_sandbox.container_name}")
        except Exception as e:
            logger.error(f"[SandboxManager] Destroy failed: {e}")

        self._active_sandbox = None
        self._stop_timeout()
        self._set_status(SandboxStatus.NONE)
        return True

    # --- State management ---

    def get_status(self) -> SandboxStatus:
        """Get current sandbox status"""
        return self._status

    def get_info(self) -> Optional[SandboxInfo]:
        """Get info about the running sandbox"""
        return self._active_sandbox

    def get_vnc_url(self) -> Optional[str]:
        """Get NoVNC connection URL"""
        if self._active_sandbox:
            return self._active_sandbox.vnc_url
        return None

    # --- Internal helpers ---

    def _get_container(self):
        """Get the active container object"""
        if not self._active_sandbox:
            return None
        client = self._get_client()
        if not client:
            return None
        try:
            container = client.containers.get(self._active_sandbox.container_name)
            if container.status == "running":
                return container
        except Exception as e:
            logger.debug(f"[SandboxManager] Active container lookup failed: {e}")
        return None

    def _set_status(self, status: SandboxStatus):
        """Update status and fire signal"""
        self._status = status
        self.statusChanged.emit(status.value)

    def _validate_sandbox_path(self, path: str) -> bool:
        """Path traversal check (validates as POSIX path inside sandbox)"""
        import posixpath
        normalized = posixpath.normpath(path)
        if ".." in normalized.split("/"):
            return False
        # Absolute paths must be under /workspace
        if path.startswith("/") and not normalized.startswith("/workspace"):
            return False
        return True

    def _start_timeout(self, minutes: int):
        """Start timeout timer"""
        self._stop_timeout()
        self._timeout_timer = threading.Timer(minutes * 60, self._on_timeout)
        self._timeout_timer.daemon = True
        self._timeout_timer.start()

    def _stop_timeout(self):
        """Stop timeout timer"""
        if self._timeout_timer:
            self._timeout_timer.cancel()
            self._timeout_timer = None

    def _on_timeout(self):
        """Timeout callback"""
        logger.info("[SandboxManager] Sandbox timeout — auto-destroying")
        if self._active_sandbox and self._active_sandbox.config and self._active_sandbox.config.auto_cleanup:
            self.destroy()
        else:
            self._set_status(SandboxStatus.STOPPED)

    def get_container_stats(self) -> Optional[dict]:
        """Get container resource usage statistics"""
        container = self._get_container()
        if not container:
            return None
        try:
            stats = container.stats(stream=False)
            # CPU usage calculation
            cpu_delta = stats["cpu_stats"]["cpu_usage"]["total_usage"] - \
                        stats["precpu_stats"]["cpu_usage"]["total_usage"]
            system_delta = stats["cpu_stats"]["system_cpu_usage"] - \
                           stats["precpu_stats"]["system_cpu_usage"]
            cpu_percent = (cpu_delta / system_delta) * 100.0 if system_delta > 0 else 0.0

            # Memory usage
            mem_usage = stats["memory_stats"].get("usage", 0)
            mem_limit = stats["memory_stats"].get("limit", 0)
            mem_mb = mem_usage / (1024 * 1024)

            return {
                "cpu_percent": round(cpu_percent, 1),
                "memory_mb": round(mem_mb, 1),
                "memory_limit_mb": round(mem_limit / (1024 * 1024), 1),
            }
        except Exception:
            return None
