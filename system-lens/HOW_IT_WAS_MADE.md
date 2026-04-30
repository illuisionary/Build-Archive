# How system-lens Was Made

This project follows the same basic pattern as the MCP "Build a server" guide, but instead of exposing weather tools, it exposes one local diagnostics tool for checking system health from an MCP client.

Reference: https://modelcontextprotocol.io/docs/develop/build-server

## Goal

`system-lens` lets an LLM inspect local machine vitals through MCP without needing shell access for every question. The main use case is asking things like:

> Is my computer slow because of Chrome, memory pressure, disk space, or another process?

The server answers that by returning CPU, memory, swap, disk, host, and process data in one structured response.

## Project Setup

The project is a small Python MCP server managed with `uv`.

Key dependencies:

- `mcp[cli]` for the MCP SDK and `FastMCP`
- `psutil` for system, disk, memory, and process stats
- `httpx` is present from the starter setup, though this server does not need an external API

The entry point is split into two files:

- `system.py` contains the actual MCP server and tool
- `main.py` imports and runs `system.main()`

## Server Instance

The MCP server is created with `FastMCP`:

```python
mcp = FastMCP("system-lens")
```

That name is what the MCP client sees when it launches the server. `FastMCP` also uses the tool function's type hints and docstring to describe the tool to the client.

## Helper Functions

Before registering the tool, `system.py` defines a few helpers:

- `_bytes_to_gib()` converts raw byte counts into readable GiB values.
- `_process_matches()` checks whether a process matches a filter by PID, name, username, or command line.
- `_sample_processes()` primes CPU measurement, waits briefly, then returns processes for a more useful CPU sample.
- `_process_info()` safely extracts process details while handling inaccessible or exited processes.

These helpers keep the MCP tool focused on assembling the final response instead of mixing formatting, filtering, and process safety in one large block.

## MCP Tool

The server exposes one tool:

```python
@mcp.tool()
def get_system_stats(
    process_filter: str | None = None,
    top_n: int = 10,
    disk_path: str = "/",
    sample_seconds: float = 0.2,
) -> dict[str, Any]:
```

The arguments make the tool flexible without making the client choose too much:

- `process_filter` narrows results to a process name, PID, username, or command text.
- `top_n` controls how many process rows come back.
- `disk_path` lets the user inspect a specific filesystem path.
- `sample_seconds` controls the CPU sampling window.

The implementation clamps `top_n` and `sample_seconds` so calls stay bounded. It returns a dictionary with sections for:

- host details
- CPU usage and load average
- memory and swap
- disk usage
- matching processes sorted by CPU, then memory

Returning structured data makes it easier for an LLM client to summarize what matters instead of parsing plain text.

## Running the Server

The server runs over stdio, which is the normal local MCP transport:

```python
def main() -> None:
    mcp.run()
```

Run it locally with:

```bash
uv run python system.py
```

For an MCP client, configure it with an absolute project path:

```json
{
  "mcpServers": {
    "system-lens": {
      "command": "uv",
      "args": [
        "--directory",
        "/Users/Luis/Documents/Projects/Build-Archive/system-lens",
        "run",
        "python",
        "system.py"
      ]
    }
  }
}
```

## Important MCP Detail

Because this is a stdio MCP server, normal tool output must go through MCP responses, not random `print()` calls to stdout. Writing logs or debug text to stdout can corrupt the JSON-RPC stream between the client and server. If debugging is needed, use stderr or a logging setup that does not write to stdout.
