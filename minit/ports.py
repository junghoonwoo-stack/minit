from __future__ import annotations

import socket
from pathlib import Path

from minit.registry import RegistryError, list_registered_apps


class PortAllocationError(RuntimeError):
    pass


def _port_bind_available(port: int) -> bool:
    if not 1 <= int(port) <= 65535:
        return False
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("127.0.0.1", int(port)))
        return True
    except OSError:
        return False
    finally:
        sock.close()


def reserved_local_ports(exclude_project: Path | None = None) -> set[int]:
    excluded = exclude_project.resolve() if exclude_project is not None else None
    try:
        entries = list_registered_apps()
    except RegistryError as exc:
        raise PortAllocationError(
            "Could not safely allocate a local port because the Minit app registry is invalid."
        ) from exc

    reserved: set[int] = set()
    for entry in entries:
        project_text = entry.get("project_dir")
        if excluded is not None and isinstance(project_text, str):
            try:
                if Path(project_text).expanduser().resolve() == excluded:
                    continue
            except OSError:
                pass
        try:
            port = int(entry.get("port"))
        except (TypeError, ValueError):
            continue
        if 1 <= port <= 65535:
            reserved.add(port)
    return reserved


def choose_available_port(
    preferred: int,
    project_dir: Path | None = None,
    scan: int = 100,
) -> int:
    """Choose an unbound, unreserved localhost port near a preferred port.

    This is used only for ports Minit is free to choose. Explicit user/app ports
    are never silently changed by this helper.
    """
    preferred = int(preferred)
    if not 1 <= preferred <= 65535:
        raise PortAllocationError("preferred port must be between 1 and 65535")
    if scan < 1:
        raise PortAllocationError("port scan size must be positive")

    reserved = reserved_local_ports(project_dir)
    upper = min(65535, preferred + scan - 1)
    for port in range(preferred, upper + 1):
        if port in reserved:
            continue
        if _port_bind_available(port):
            return port

    raise PortAllocationError(
        f"Could not find a free local port in {preferred}-{upper}. Use `minit deploy --port <port>` explicitly."
    )
