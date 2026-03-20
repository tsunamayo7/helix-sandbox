# AGENTS.md — helix-sandbox

## Shared Memory (Mem0)

Shared memory server is running at `localhost:8080`.

### Search: `curl -s -X POST http://localhost:8080/search -H "Content-Type: application/json" -d "{\"query\": \"search term\"}"`
### Save: `curl -s -X POST http://localhost:8080/add -H "Content-Type: application/json" -d "{\"text\": \"content to save\"}"`

### Rules
- Search for related memories at session start
- Save important decisions when user says "remember"

## Project Info
- MCP server for Windows Sandbox programmatic control
- Language: Python 3.12, package manager: uv
- Test: `uv run pytest`
