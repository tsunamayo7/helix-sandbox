<div align="center">

# helix-sandbox

**Secure sandbox MCP server for AI agents — Docker and Windows Sandbox backends**

Give your AI agent a safe playground to execute code, edit files, and interact with a GUI desktop — without risking your host system.

[![CI](https://github.com/tsunamayo7/helix-sandbox/actions/workflows/ci.yml/badge.svg)](https://github.com/tsunamayo7/helix-sandbox/actions/workflows/ci.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![MCP](https://img.shields.io/badge/MCP-compatible-8A2BE2?logo=data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjQiIGhlaWdodD0iMjQiIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48Y2lyY2xlIGN4PSIxMiIgY3k9IjEyIiByPSIxMCIgc3Ryb2tlPSJ3aGl0ZSIgc3Ryb2tlLXdpZHRoPSIyIi8+PC9zdmc+)](https://modelcontextprotocol.io/)
[![Docker](https://img.shields.io/badge/Docker-supported-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![Windows Sandbox](https://img.shields.io/badge/Windows_Sandbox-supported-0078D6?logo=windows&logoColor=white)](https://learn.microsoft.com/en-us/windows/security/application-security/application-isolation/windows-sandbox/windows-sandbox-overview)
[![GitHub stars](https://img.shields.io/github/stars/tsunamayo7/helix-sandbox?style=social)](https://github.com/tsunamayo7/helix-sandbox/stargazers)

</div>

---

## Why helix-sandbox?

Running untrusted code from AI agents on your host machine is dangerous. Cloud sandboxes cost money and require internet. **helix-sandbox** solves both problems:

| | helix-sandbox | Cloud sandboxes (E2B, Cua, Daytona) |
|---|:---:|:---:|
| **Runs locally** | Yes | No |
| **Zero cloud cost** | Yes | Paid |
| **Works offline** | Yes | No |
| **Docker backend** | Yes | Varies |
| **Windows Sandbox backend** | Yes | No |
| **GUI automation** | Yes | Limited |
| **MCP protocol** | Yes | No |

**What makes helix-sandbox unique:**

- **Dual backend** — Docker (Linux containers) + Windows Sandbox (native Windows 11) in one server
- **AI-safety focused** — Path traversal protection, circuit breaker, network isolation
- **10 MCP tools** — Create, destroy, execute, file I/O, screenshots, diffs, stats
- **GUI desktop access** — VNC/noVNC (Docker) or native window (Windows Sandbox)
- **Promotion engine** — Safely review and apply sandbox changes back to the host
- **No vendor lock-in** — Open source, local-first, works with any MCP client

## How It Works

```
AI Agent (Claude Code / Codex CLI / Open WebUI / ...)
                    | MCP Protocol
            helix-sandbox server
                    |
       +------------+------------+
       Docker Desktop            Windows Sandbox
       (Linux container)         (Windows 11 native)
       - Multiple instances      - Ephemeral by design
       - Configurable persist    - Native Windows GUI
       - VNC desktop access      - Pilot Bridge GUI
```

## MCP Tools

| Tool | Description |
|------|-------------|
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

## Backend Comparison

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

### 1. Install

```bash
git clone https://github.com/tsunamayo7/helix-sandbox.git
cd helix-sandbox
uv sync
```

### 2. Build Docker Image (Docker backend)

```bash
# Windows (PowerShell)
.\scripts\build_sandbox_image.ps1

# Linux/macOS
./scripts/build_sandbox_image.sh
```

### 3. Connect to Your AI Agent

<details>
<summary><strong>Claude Code</strong></summary>

Add to your Claude Code MCP settings (`~/.claude/settings.json`):

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

</details>

<details>
<summary><strong>Claude Desktop</strong></summary>

Add to `claude_desktop_config.json`:

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

</details>

<details>
<summary><strong>Codex CLI / Other MCP Clients</strong></summary>

Any MCP-compatible client can connect. Point it to:

```bash
uv --directory /path/to/helix-sandbox run server.py
```

</details>

## Usage Examples

Once connected, ask your AI agent:

```
"Create a sandbox and run python --version inside it"
```

```
"Write a Python script to the sandbox that generates a Fibonacci sequence, execute it, and show me the output"
```

```
"Take a screenshot of the sandbox desktop"
```

```
"Show me what files changed in the sandbox, then apply the changes to my host"
```

```
"Create a sandbox, install numpy, run a matrix multiplication benchmark, and show me the stats"
```

## Compatible MCP Clients

helix-sandbox works with any client that supports the [Model Context Protocol](https://modelcontextprotocol.io/):

| Client | Status | Notes |
|--------|--------|-------|
| [Claude Code](https://claude.ai/code) | Tested | Primary development target |
| [Claude Desktop](https://claude.ai/download) | Compatible | Via MCP config |
| [Codex CLI](https://github.com/openai/codex) | Compatible | Via MCP config |
| [Open WebUI](https://github.com/open-webui/open-webui) | Compatible | Via MCP proxy |
| [Continue](https://github.com/continuedev/continue) | Compatible | Via MCP config |
| Any MCP client | Compatible | Standard MCP protocol |

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

- **Backend Abstraction** — `BackendCapability` flags adapt behavior per backend
- **Dual Backend** — Docker for Linux containers, Windows Sandbox for native Windows
- **2-Stage Fallback** — Docker SDK to CLI fallback for resilience
- **Path Traversal Protection** — All file operations validate against directory traversal attacks
- **Circuit Breaker** — Connection protection for unreliable Docker connections
- **Promotion Engine** — Safely apply sandbox changes back to the host

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
| Open source | MIT | Partial | Yes | Yes |

## Development

```bash
# Install dev dependencies
uv sync --dev

# Run tests
uv run python -m pytest tests/ -v

# Lint
uv run ruff check src/ server.py tests/

# System info
uv run python main.py --info
```

## Requirements

- Python 3.12+
- **Docker backend**: Docker Desktop or Rancher Desktop
- **Windows Sandbox backend**: Windows 11 Pro/Enterprise/Education

## Related Projects

| Project | Description |
|---------|-------------|
| [helix-ai-studio](https://github.com/tsunamayo7/helix-ai-studio) | All-in-one AI chat studio with 7 providers, RAG, MCP tools, and pipeline |
| [helix-pilot](https://github.com/tsunamayo7/helix-pilot) | GUI automation MCP server — AI controls Windows desktop via local Vision LLM |
| [helix-agent](https://github.com/tsunamayo7/helix-agent) | Extend Claude Code with local Ollama models — cut token costs by 60-80% |
| [claude-code-codex-agents](https://github.com/tsunamayo7/claude-code-codex-agents) | MCP bridge to Codex CLI (GPT-5.4) with structured JSONL traces |

## Contributing

Contributions are welcome! Feel free to:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

Bug reports and feature requests via [Issues](https://github.com/tsunamayo7/helix-sandbox/issues) are also appreciated.

## License

[MIT](LICENSE)

---

<div align="center">

**If you find helix-sandbox useful, please consider giving it a star!**

[![Star this repo](https://img.shields.io/github/stars/tsunamayo7/helix-sandbox?style=social)](https://github.com/tsunamayo7/helix-sandbox)

Built with [FastMCP](https://github.com/jlowin/fastmcp) and [Model Context Protocol](https://modelcontextprotocol.io/)

</div>
