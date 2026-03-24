"""Test MCP tool registration in server.py"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def test_mcp_instance():
    from server import mcp
    assert mcp is not None
    assert mcp.name == "helix-sandbox"


def test_tool_count():
    from server import mcp
    tools = asyncio.run(mcp.list_tools())
    assert len(tools) >= 10, f"Expected at least 10 tools, got {len(tools)}"


def test_tool_names():
    from server import mcp
    tools = asyncio.run(mcp.list_tools())
    expected = [
        "create_sandbox",
        "destroy_sandbox",
        "sandbox_status",
        "execute_command",
        "read_file",
        "write_file",
        "list_directory",
        "screenshot",
        "get_diff",
        "container_stats",
    ]
    registered = {t.name for t in tools}
    for name in expected:
        assert name in registered, f"Tool '{name}' not registered. Found: {registered}"
