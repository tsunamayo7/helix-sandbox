# helix-sandbox

Secure sandbox MCP server for AI agents. Run code, edit files, and operate GUI in isolated Docker or Windows Sandbox environments.

[![CI](https://github.com/tsunamayo7/helix-sandbox/actions/workflows/ci.yml/badge.svg)](https://github.com/tsunamayo7/helix-sandbox/actions/workflows/ci.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## What It Does

helix-sandbox gives AI agents (Claude Code, Codex CLI, Open WebUI, etc.) a **safe, isolated environment** to execute code, read/write files, and even interact with a GUI desktop — without touching your host system.

```
AI Agent (Claude Code / Codex CLI / Open WebUI)
            | MCP Protocol
    helix-sandbox server
            |
   +--------+--------+
   Docker Desktop    Windows Sandbox
   (Linux container) (Windows 11 native)
```

## Features

| MCP Tool | Description |
|----------|-------------|
| `create_sandbox` | Create and start an isolated sandbox |
| `destroy_sandbox` | Stop and remove the sandbox |
| `sandbox_status` | Get current sandbox state and backend info |
| `execute_command` | Run shell commands inside the sandbox |
| `read_file` | Read file contents from the sandbox |
| `write_file` | Write files into the sandbox |
| `list_directory` | List directory contents |
| `screenshot` | Capture desktop screenshot (base64 PNG) |
| `get_diff` | Get workspace change diff |
| `container_stats` | CPU/RAM usage statistics |

### Backend Comparison

| Feature | Docker | Windows Sandbox |
|---------|:------:|:---------------:|
| Concurrent instances | Multiple | Single |
| Persistence | Configurable | Ephemeral |
| GUI desktop | VNC + noVNC | Native window |
| OS inside | Linux (Ubuntu) | Windows 11 |
| Requires | Docker Desktop | Windows 11 Pro |
| Network isolation | Configurable | Configurable |
| Resource limits | CPU/RAM | RAM/vGPU |
| Screenshot | Via X11 capture | Via Pilot Bridge |

## Quick Start

### Installation

```bash
git clone https://github.com/tsunamayo7/helix-sandbox.git
cd helix-sandbox
uv sync
```

### Build Docker Image (Docker backend)

```bash
# Windows (PowerShell)
.\scripts\build_sandbox_image.ps1

# Linux/macOS
./scripts/build_sandbox_image.sh
```

### Claude Code Integration

Add to your Claude Code MCP settings:

```json
{
  "mcpServers": {
    "helix-sandbox": {
      "command": "uv",
      "args": ["--directory", "/path/to/helix-sandbox", "run", "server.py"]
    }
  }
}
```

## Usage Examples

Once connected, ask your AI agent:

- *"Create a sandbox and run `python --version` inside it"*
- *"Write a Python script to the sandbox, execute it, and show me the output"*
- *"Take a screenshot of the sandbox desktop"*
- *"Show me what files changed in the sandbox"*

## Architecture

```
helix-sandbox/
├── server.py                    # FastMCP server (10 MCP tools)
├── main.py                      # CLI entry point
├── docker/sandbox/Dockerfile    # Docker sandbox image
├── src/
│   ├── sandbox/
│   │   ├── backend_base.py      # Abstract backend (BackendCapability flags)
│   │   ├── backend_factory.py   # Auto-detect and create backends
│   │   ├── docker_backend.py    # Docker Desktop / Rancher adapter
│   │   ├── windows_sandbox_backend.py  # Windows Sandbox adapter
│   │   ├── sandbox_manager.py   # Docker container CRUD and file ops
│   │   ├── sandbox_config.py    # Configuration dataclasses
│   │   ├── circuit_breaker.py   # Connection resilience pattern
│   │   └── promotion_engine.py  # Diff detection and host promotion
│   ├── tools/
│   │   └── sandbox_pilot_bridge.py  # GUI automation bridge
│   └── utils/
│       ├── platform_utils.py    # Cross-platform helpers
│       └── subprocess_utils.py  # Hidden process execution
├── scripts/
│   ├── build_sandbox_image.ps1  # Docker image build (Windows)
│   ├── build_sandbox_image.sh   # Docker image build (Linux/macOS)
│   └── wsb_pilot_agent.py       # Agent inside Windows Sandbox
└── tests/                       # pytest test suite (20 tests)
```

### Key Design Patterns

- **Backend Abstraction**: `BackendCapability` flags adapt behavior per backend
- **Dual Backend**: Docker for Linux containers, Windows Sandbox for native Windows
- **2-Stage Fallback**: Docker SDK to CLI fallback for resilience
- **Path Traversal Protection**: All file operations validate against directory traversal
- **Circuit Breaker**: Connection protection for unreliable Docker connections
- **Promotion Engine**: Safely apply sandbox changes back to the host

## Comparison with Alternatives

| Feature | helix-sandbox | E2B | Cua | Daytona |
|---------|:------------:|:---:|:---:|:-------:|
| Local execution | Yes | Cloud | Cloud | Cloud |
| Docker backend | Yes | - | - | Yes |
| Windows Sandbox | Yes | - | - | - |
| MCP protocol | Yes | - | - | - |
| GUI automation | Yes | - | Yes | - |
| No cloud costs | Yes | Paid | Paid | Paid |
| Offline capable | Yes | - | - | - |

**Unique combination**: Local + Docker + Windows Sandbox + MCP + GUI automation + zero cloud cost

## Development

```bash
uv sync --dev
uv run python -m pytest tests/ -v
uv run ruff check src/ server.py tests/
uv run python main.py --info
```

## Requirements

- Python 3.12+
- **Docker backend**: Docker Desktop or Rancher Desktop
- **Windows Sandbox backend**: Windows 11 Pro/Enterprise/Education

## License

MIT
