# system-lens

An MCP server that exposes local system vitals to an LLM.

## Tool

`get_system_stats(process_filter=None, top_n=10, disk_path="/", sample_seconds=0.2)`

Returns:

- CPU usage, core counts, per-core usage, and load average
- RAM and swap usage
- Disk usage for a requested path
- Top processes by CPU and memory
- Optional process matching by name, PID, username, or command-line text

Example prompt:

> Check whether my computer is running slow because of Chrome.

The model can call:

```python
get_system_stats(process_filter="Chrome")
```

## Run locally

```bash
uv run python system.py
```

## MCP client config

Use this server over stdio:

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
