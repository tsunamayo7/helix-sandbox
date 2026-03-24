"""Test backend base classes and signal replacement."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.sandbox.backend_base import BackendCapability, SandboxBackend, _Signal


def test_signal_emit_and_connect():
    sig = _Signal()
    received = []
    sig.connect(lambda msg: received.append(msg))
    sig.emit("hello")
    sig.emit("world")
    assert received == ["hello", "world"]


def test_signal_multiple_listeners():
    sig = _Signal()
    a, b = [], []
    sig.connect(lambda x: a.append(x))
    sig.connect(lambda x: b.append(x))
    sig.emit("test")
    assert a == ["test"]
    assert b == ["test"]


def test_signal_error_isolation():
    sig = _Signal()
    results = []
    sig.connect(lambda x: (_ for _ in ()).throw(ValueError("boom")))
    sig.connect(lambda x: results.append(x))
    sig.emit("ok")
    # Second listener should still receive despite first raising
    assert results == ["ok"]


def test_backend_capability_flags():
    caps = BackendCapability.FILE_BROWSE | BackendCapability.EXEC_COMMAND
    assert BackendCapability.FILE_BROWSE in caps
    assert BackendCapability.EXEC_COMMAND in caps
    assert BackendCapability.SCREENSHOT not in caps


def test_backend_capability_none():
    assert BackendCapability.NONE.value == 0


def test_sandbox_backend_is_abstract():
    """SandboxBackend cannot be instantiated directly."""
    # Not using pytest.raises because SandboxBackend has abstract methods
    # that prevent instantiation via normal ABC mechanism
    class ConcreteBackend(SandboxBackend):
        def backend_type(self): return "test"
        def capabilities(self): return BackendCapability.NONE
        def is_available(self): return True
        def get_unavailable_reason(self): return ""
        def create(self, config): return None
        def destroy(self): return True
        def get_status(self):
            from src.sandbox.sandbox_config import SandboxStatus
            return SandboxStatus.NONE

    b = ConcreteBackend()
    assert b.backend_type() == "test"
    assert b.is_available() is True
    assert b.screenshot() is None
    assert b.list_files() == []
    assert b.read_file("/test") == b""
    assert b.get_container_stats() is None


def test_concrete_backend_signals():
    class ConcreteBackend(SandboxBackend):
        def backend_type(self): return "test"
        def capabilities(self): return BackendCapability.NONE
        def is_available(self): return True
        def get_unavailable_reason(self): return ""
        def create(self, config): return None
        def destroy(self): return True
        def get_status(self):
            from src.sandbox.sandbox_config import SandboxStatus
            return SandboxStatus.NONE

    b = ConcreteBackend()
    received = []
    b.statusChanged.connect(lambda s: received.append(s))
    b.statusChanged.emit("running")
    assert received == ["running"]
