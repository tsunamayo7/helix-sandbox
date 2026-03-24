"""Tests for sandbox file operation helpers."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.sandbox.docker_backend import DockerBackend
from src.sandbox.sandbox_manager import SandboxManager


class _ExecResult:
    def __init__(self, exit_code=0, output=b""):
        self.exit_code = exit_code
        self.output = output


class _Container:
    def __init__(self, exit_code=0, output=b""):
        self.calls = []
        self._exit_code = exit_code
        self._output = output

    def exec_run(self, cmd, workdir="/workspace", demux=False):
        self.calls.append({"cmd": cmd, "workdir": workdir, "demux": demux})
        return _ExecResult(self._exit_code, self._output)


def test_write_file_handles_quotes_and_newlines():
    mgr = SandboxManager()
    container = _Container()
    mgr._get_container = lambda: container

    text = "print(\"Hello\")\nprint('world')\n"
    result = mgr.write_file("/workspace/test.py", text)

    assert result == {"success": True, "path": "/workspace/test.py"}
    cmd = container.calls[0]["cmd"][2]
    assert "base64.b64decode" in cmd
    assert "print(\\\"Hello\\\")" not in cmd


def test_docker_backend_read_file_preserves_error_dict():
    backend = DockerBackend()
    backend.manager.read_file = lambda path: {"error": "Invalid path: path traversal detected"}

    result = backend.read_file("/workspace/../etc/passwd")

    assert result == {"error": "Invalid path: path traversal detected"}
