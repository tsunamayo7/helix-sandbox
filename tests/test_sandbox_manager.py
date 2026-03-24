"""Test SandboxManager path validation and utility methods."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.sandbox.sandbox_manager import SandboxManager, _find_free_port


def test_path_validation_normal():
    mgr = SandboxManager()
    assert mgr._validate_sandbox_path("/workspace/main.py") is True
    assert mgr._validate_sandbox_path("/workspace/src/app.py") is True
    assert mgr._validate_sandbox_path("main.py") is True


def test_path_validation_traversal():
    mgr = SandboxManager()
    assert mgr._validate_sandbox_path("/workspace/../etc/passwd") is False
    assert mgr._validate_sandbox_path("../../etc/shadow") is False


def test_path_validation_outside_workspace():
    mgr = SandboxManager()
    assert mgr._validate_sandbox_path("/etc/passwd") is False
    assert mgr._validate_sandbox_path("/root/.ssh/id_rsa") is False


def test_find_free_port():
    port = _find_free_port(49152, 49160)
    assert 49152 <= port < 49160


def test_sandbox_manager_initial_status():
    from src.sandbox.sandbox_config import SandboxStatus
    mgr = SandboxManager()
    assert mgr.get_status() == SandboxStatus.NONE
    assert mgr.get_info() is None
    assert mgr.get_vnc_url() is None


def test_sandbox_manager_signals():
    mgr = SandboxManager()
    received = []
    mgr.statusChanged.connect(lambda s: received.append(s))
    mgr.errorOccurred.connect(lambda e: received.append(f"error:{e}"))
    mgr.statusChanged.emit("test")
    mgr.errorOccurred.emit("fail")
    assert received == ["test", "error:fail"]
