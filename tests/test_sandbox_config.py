"""Test sandbox configuration data classes."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.sandbox.sandbox_config import SandboxConfig, SandboxInfo, SandboxStatus


def test_sandbox_status_values():
    assert SandboxStatus.NONE.value == "none"
    assert SandboxStatus.CREATING.value == "creating"
    assert SandboxStatus.RUNNING.value == "running"
    assert SandboxStatus.STOPPED.value == "stopped"
    assert SandboxStatus.ERROR.value == "error"


def test_sandbox_config_defaults():
    config = SandboxConfig()
    assert config.image_name == "helix-sandbox:latest"
    assert config.timeout_minutes == 60
    assert config.auto_cleanup is True
    assert config.network_mode == "none"
    assert config.cpu_limit == 2.0
    assert config.memory_limit == "2g"


def test_sandbox_config_custom():
    config = SandboxConfig(
        workspace_path="/tmp/test",
        timeout_minutes=60,
        cpu_limit=4.0,
    )
    assert config.workspace_path == "/tmp/test"
    assert config.timeout_minutes == 60
    assert config.cpu_limit == 4.0


def test_sandbox_info():
    config = SandboxConfig()
    info = SandboxInfo(
        sandbox_id="abc123",
        container_name="test-container",
        status=SandboxStatus.RUNNING,
        vnc_url="http://localhost:6080",
        vnc_port=5900,
        novnc_port=6080,
        workspace_path="/workspace",
        config=config,
    )
    assert info.sandbox_id == "abc123"
    assert info.status == SandboxStatus.RUNNING
    assert info.vnc_url == "http://localhost:6080"
