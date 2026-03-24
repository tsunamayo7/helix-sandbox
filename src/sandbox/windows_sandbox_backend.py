"""helix-sandbox — Windows Sandbox backend

Uses Windows Sandbox (built into Windows 11 Pro/Enterprise/Education) to provide
an isolated environment. No Docker Desktop required.

Constraints:
- Only one instance at a time
- Ephemeral (all data lost on exit, persist via MappedFolder)
- External window only (no in-app embedding)
- No container exec API (limited support on 24H2+)
"""

import logging
import os
import platform
import subprocess
import tempfile
import threading
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional

from .backend_base import BackendCapability, SandboxBackend
from .sandbox_config import SandboxInfo, SandboxStatus

logger = logging.getLogger(__name__)


class WindowsSandboxBackend(SandboxBackend):
    """Windows Sandbox backend"""

    def __init__(self):
        super().__init__()
        self._status = SandboxStatus.NONE
        self._wsb_path: Optional[str] = None
        self._process: Optional[subprocess.Popen] = None
        self._workspace_path: str = ""
        self._sandbox_info: Optional[SandboxInfo] = None

        # Process monitor timer
        self._monitor_timer: Optional[threading.Timer] = None
        self._monitor_interval = 3.0  # seconds

    # --- Required methods ---

    def backend_type(self) -> str:
        return "windows_sandbox"

    def capabilities(self) -> BackendCapability:
        return BackendCapability.DIFF_PROMOTE

    def is_available(self) -> bool:
        """Check if Windows Sandbox is available"""
        if platform.system() != "Windows":
            return False
        wsb_exe = self._get_wsb_exe_path()
        return wsb_exe.exists()

    def get_unavailable_reason(self) -> str:
        """Return reason when unavailable"""
        if platform.system() != "Windows":
            return "Windows Sandbox is only available on Windows."

        wsb_exe = self._get_wsb_exe_path()
        if not wsb_exe.exists():
            return (
                "Windows Sandbox is not enabled.\n\n"
                "How to enable:\n"
                "1. Settings > Apps > Optional features > More Windows features\n"
                "2. Check 'Windows Sandbox'\n"
                "3. Restart your PC\n\n"
                "Requires Windows 11 Pro / Enterprise / Education.\n"
                "Enable virtualization (VT-x / AMD-V) in BIOS."
            )

        return ""

    def create(self, config) -> Optional[SandboxInfo]:
        """Start Windows Sandbox"""
        if not self.is_available():
            self.errorOccurred.emit(self.get_unavailable_reason())
            return None

        # Check for existing process
        if self._is_sandbox_running():
            self.errorOccurred.emit(
                "Windows Sandbox is already running.\n"
                "Only one instance can run at a time.\n"
                "Close the existing sandbox and try again."
            )
            return None

        self._set_status(SandboxStatus.CREATING)

        try:
            # Get workspace path
            workspace = getattr(config, 'workspace_path', '')
            if not workspace:
                workspace = str(Path.cwd())
            self._workspace_path = workspace

            # Generate .wsb config file
            wsb_config = self._generate_wsb_config(config)
            self._wsb_path = self._write_wsb_file(wsb_config)

            # Start Windows Sandbox
            wsb_exe = str(self._get_wsb_exe_path())
            self._process = subprocess.Popen(
                [wsb_exe, self._wsb_path],
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0,
            )

            # Generate SandboxInfo
            self._sandbox_info = SandboxInfo(
                sandbox_id=f"wsb-{self._process.pid}",
                container_name="WindowsSandbox",
                status=SandboxStatus.RUNNING,
                backend_type="windows_sandbox",
                vnc_url="",
                workspace_path=self._workspace_path,
            )

            self._set_status(SandboxStatus.RUNNING)
            self._start_monitor()

            logger.info(f"[WindowsSandbox] Started (PID: {self._process.pid})")
            return self._sandbox_info

        except FileNotFoundError:
            self.errorOccurred.emit("WindowsSandbox.exe not found.")
            self._set_status(SandboxStatus.ERROR)
            return None
        except Exception as e:
            logger.error(f"[WindowsSandbox] Start failed: {e}")
            self.errorOccurred.emit(f"Windows Sandbox failed to start: {e}")
            self._set_status(SandboxStatus.ERROR)
            return None

    def destroy(self) -> bool:
        """Stop Windows Sandbox"""
        self._stop_monitor()

        try:
            # Kill WindowsSandbox.exe via taskkill
            subprocess.run(
                ["taskkill", "/F", "/IM", "WindowsSandbox.exe"],
                capture_output=True, timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0,
            )
            logger.info("[WindowsSandbox] Stopped via taskkill")
        except Exception as e:
            logger.warning(f"[WindowsSandbox] taskkill failed: {e}")

        self._process = None
        self._sandbox_info = None
        self._set_status(SandboxStatus.STOPPED)

        # Delete temporary .wsb file
        self._cleanup_wsb_file()

        return True

    def get_status(self) -> SandboxStatus:
        return self._status

    # --- Optional methods ---

    def get_diff(self) -> str:
        """Detect changes via MappedFolder"""
        if not self._workspace_path or not Path(self._workspace_path).exists():
            return ""

        try:
            _cflags = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            result = subprocess.run(
                ["git", "diff"],
                capture_output=True, text=True, timeout=30,
                cwd=self._workspace_path, creationflags=_cflags,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout

            # Include staged changes
            result2 = subprocess.run(
                ["git", "diff", "--cached"],
                capture_output=True, text=True, timeout=30,
                cwd=self._workspace_path, creationflags=_cflags,
            )
            if result2.returncode == 0 and result2.stdout.strip():
                return result.stdout + "\n" + result2.stdout

        except FileNotFoundError:
            logger.debug("[WindowsSandbox] git not found for diff detection")
        except Exception as e:
            logger.warning(f"[WindowsSandbox] diff detection failed: {e}")

        return ""

    def get_workspace_path(self) -> str:
        return self._workspace_path

    # --- .wsb file generation ---

    def _generate_wsb_config(self, config) -> str:
        """Generate .wsb XML from SandboxConfig / WindowsSandboxConfig"""
        root = ET.Element("Configuration")

        # VGpu
        vgpu = getattr(config, 'vgpu', 'Enable')
        ET.SubElement(root, "VGpu").text = vgpu

        # Networking
        networking = getattr(config, 'networking', 'Default')
        ET.SubElement(root, "Networking").text = networking

        # ClipboardRedirection
        clipboard = getattr(config, 'clipboard', 'Enable')
        ET.SubElement(root, "ClipboardRedirection").text = clipboard

        # MemoryInMB
        memory_mb = getattr(config, 'memory_mb', None)
        if memory_mb is None:
            # Convert from SandboxConfig (memory_limit "2g" -> 2048)
            mem_str = getattr(config, 'memory_limit', '2g')
            try:
                if isinstance(mem_str, str) and mem_str.endswith('g'):
                    memory_mb = int(mem_str[:-1]) * 1024
                elif isinstance(mem_str, (int, float)):
                    memory_mb = int(mem_str) * 1024
                else:
                    memory_mb = 2048
            except (ValueError, TypeError):
                memory_mb = 2048
        ET.SubElement(root, "MemoryInMB").text = str(memory_mb)

        # MappedFolders
        workspace = getattr(config, 'workspace_path', '')
        if workspace and Path(workspace).exists():
            mapped_folders = ET.SubElement(root, "MappedFolders")
            folder = ET.SubElement(mapped_folders, "MappedFolder")
            ET.SubElement(folder, "HostFolder").text = str(Path(workspace).resolve())
            ET.SubElement(folder, "SandboxFolder").text = r"C:\workspace"

            readonly = getattr(config, 'mount_readonly', False)
            ET.SubElement(folder, "ReadOnly").text = str(readonly).lower()

        # LogonCommand (start wsb_pilot_agent.py in background + open explorer)
        logon_cmd = getattr(config, 'logon_command', '')
        if not logon_cmd:
            if workspace:
                logon_cmd = (
                    r'powershell -ExecutionPolicy Bypass -NoProfile -Command "'
                    r"if (Test-Path 'C:\workspace\scripts\wsb_pilot_agent.py') {"
                    r" Start-Process python -ArgumentList 'C:\workspace\scripts\wsb_pilot_agent.py'"
                    r" -WindowStyle Hidden };"
                    r" Start-Process explorer -ArgumentList 'C:\workspace'"
                    r'"'
                )
            else:
                logon_cmd = "explorer.exe"
        logon = ET.SubElement(root, "LogonCommand")
        ET.SubElement(logon, "Command").text = logon_cmd

        # Convert XML to string
        ET.indent(root, space="  ")
        return ET.tostring(root, encoding="unicode", xml_declaration=False)

    def _write_wsb_file(self, xml_content: str) -> str:
        """Write temporary .wsb file"""
        temp_dir = Path(tempfile.gettempdir()) / "helix_sandbox"
        temp_dir.mkdir(exist_ok=True)

        wsb_path = temp_dir / "helix_workspace.wsb"
        wsb_path.write_text(xml_content, encoding="utf-8")
        logger.debug(f"[WindowsSandbox] WSB file written: {wsb_path}")
        return str(wsb_path)

    def _cleanup_wsb_file(self):
        """Delete temporary .wsb file"""
        if self._wsb_path:
            try:
                Path(self._wsb_path).unlink(missing_ok=True)
            except Exception as e:
                logger.debug(f"[WindowsSandboxBackend] Failed to cleanup wsb file '{self._wsb_path}': {e}")
            self._wsb_path = None

    # --- Process monitoring ---

    def _start_monitor(self):
        """Start periodic process monitoring"""
        self._stop_monitor()
        self._schedule_monitor()

    def _schedule_monitor(self):
        """Schedule the next monitor check"""
        self._monitor_timer = threading.Timer(self._monitor_interval, self._check_process)
        self._monitor_timer.daemon = True
        self._monitor_timer.start()

    def _stop_monitor(self):
        """Stop process monitoring"""
        if self._monitor_timer:
            self._monitor_timer.cancel()
            self._monitor_timer = None

    def _check_process(self):
        """Check if Windows Sandbox process is still alive"""
        if not self._is_sandbox_running():
            logger.info("[WindowsSandbox] Process terminated (detected by monitor)")
            self._monitor_timer = None
            self._process = None
            self._sandbox_info = None
            self._set_status(SandboxStatus.STOPPED)
            self._cleanup_wsb_file()
            self.statusChanged.emit("stopped")
        else:
            # Reschedule next check
            self._schedule_monitor()

    def _is_sandbox_running(self) -> bool:
        """Check if WindowsSandbox.exe is running"""
        try:
            result = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq WindowsSandbox.exe", "/NH"],
                capture_output=True, text=True, timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0,
            )
            return "WindowsSandbox.exe" in result.stdout
        except Exception:
            return False

    # --- Utilities ---

    @staticmethod
    def _get_wsb_exe_path() -> Path:
        """Return path to WindowsSandbox.exe"""
        system_root = os.environ.get("SystemRoot", r"C:\Windows")
        return Path(system_root) / "System32" / "WindowsSandbox.exe"

    def _set_status(self, status: SandboxStatus):
        """Update status and fire signal"""
        self._status = status
        self.statusChanged.emit(status.value)
