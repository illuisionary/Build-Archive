from __future__ import annotations

import os
import time
from datetime import datetime
from typing import Any

import psutil
from mcp.server.fastmcp import FastMCP


mcp = FastMCP("system-lens")


def _bytes_to_gib(value: int | float) -> float:
    return round(value / (1024**3), 2)


def _process_matches(info: dict[str, Any], process_filter: str | None) -> bool:
    if not process_filter:
        return True

    needle = process_filter.casefold()
    fields = [
        str(info.get("pid", "")),
        info.get("name") or "",
        " ".join(info.get("cmdline") or []),
        info.get("username") or "",
    ]
    return any(needle in field.casefold() for field in fields)


def _sample_processes(sample_seconds: float) -> list[psutil.Process]:
    processes: list[psutil.Process] = []

    for process in psutil.process_iter():
        try:
            process.cpu_percent(None)
            processes.append(process)
        except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess):
            continue

    time.sleep(sample_seconds)
    return processes


def _process_info(process: psutil.Process) -> dict[str, Any] | None:
    try:
        with process.oneshot():
            memory = process.memory_info()
            create_time = process.create_time()
            cmdline = process.cmdline()

            return {
                "pid": process.pid,
                "name": process.name(),
                "username": process.username(),
                "status": process.status(),
                "cpu_percent": round(process.cpu_percent(None), 1),
                "memory_rss_gib": _bytes_to_gib(memory.rss),
                "memory_vms_gib": _bytes_to_gib(memory.vms),
                "created_at": datetime.fromtimestamp(create_time).isoformat(timespec="seconds"),
                "cmdline": cmdline,
            }
    except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess):
        return None


@mcp.tool()
def get_system_stats(
    process_filter: str | None = None,
    top_n: int = 10,
    disk_path: str = "/",
    sample_seconds: float = 0.2,
) -> dict[str, Any]:
    """Return local CPU, memory, disk, and process stats.

    Args:
        process_filter: Optional process name, PID, user, or command-line text to match.
        top_n: Maximum number of process rows to return.
        disk_path: Filesystem path to inspect for disk usage.
        sample_seconds: CPU sampling window for process measurements.
    """

    safe_top_n = max(1, min(top_n, 50))
    safe_sample_seconds = max(0.1, min(sample_seconds, 2.0))

    cpu_percent = psutil.cpu_percent(interval=safe_sample_seconds, percpu=False)
    cpu_per_core = psutil.cpu_percent(interval=None, percpu=True)
    memory = psutil.virtual_memory()
    swap = psutil.swap_memory()
    disk = psutil.disk_usage(disk_path)

    process_rows = []
    for process in _sample_processes(safe_sample_seconds):
        info = _process_info(process)
        if info and _process_matches(info, process_filter):
            process_rows.append(info)

    process_rows.sort(
        key=lambda item: (item["cpu_percent"], item["memory_rss_gib"]),
        reverse=True,
    )

    return {
        "host": {
            "hostname": os.uname().nodename,
            "platform": os.uname().sysname,
            "platform_release": os.uname().release,
            "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat(timespec="seconds"),
        },
        "cpu": {
            "logical_cores": psutil.cpu_count(logical=True),
            "physical_cores": psutil.cpu_count(logical=False),
            "usage_percent": round(cpu_percent, 1),
            "per_core_percent": [round(value, 1) for value in cpu_per_core],
            "load_average": os.getloadavg() if hasattr(os, "getloadavg") else None,
        },
        "memory": {
            "total_gib": _bytes_to_gib(memory.total),
            "available_gib": _bytes_to_gib(memory.available),
            "used_gib": _bytes_to_gib(memory.used),
            "usage_percent": memory.percent,
        },
        "swap": {
            "total_gib": _bytes_to_gib(swap.total),
            "used_gib": _bytes_to_gib(swap.used),
            "usage_percent": swap.percent,
        },
        "disk": {
            "path": disk_path,
            "total_gib": _bytes_to_gib(disk.total),
            "used_gib": _bytes_to_gib(disk.used),
            "free_gib": _bytes_to_gib(disk.free),
            "usage_percent": disk.percent,
        },
        "processes": {
            "filter": process_filter,
            "returned": min(len(process_rows), safe_top_n),
            "matches": len(process_rows),
            "sort": "cpu_percent desc, memory_rss_gib desc",
            "items": process_rows[:safe_top_n],
        },
    }


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
