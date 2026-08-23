from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from minit.ports import PortAllocationError, choose_available_port
from minit.service import load_service_spec


class DetectionError(RuntimeError):
    pass


@dataclass(frozen=True)
class DeployPlan:
    command: list[str]
    port: int
    kind: str
    source: str


PORT_PATTERNS = (
    re.compile(r"(?:--port|--server\.port|-p)\s*[= ]\s*(\d{2,5})", re.IGNORECASE),
    re.compile(r"\bPORT\s*=\s*[\"']?(\d{2,5})", re.IGNORECASE),
    re.compile(r"\bport\s*=\s*(\d{2,5})", re.IGNORECASE),
    re.compile(r"\blisten\s*\(\s*(\d{2,5})", re.IGNORECASE),
    re.compile(r"(?:ThreadingHTTPServer|HTTPServer)\s*\(\s*\([^,]+,\s*(\d{2,5})", re.IGNORECASE),
)


def _valid_port(value: int) -> bool:
    return 1 <= value <= 65535


def _first_port(text: str) -> int | None:
    for pattern in PORT_PATTERNS:
        match = pattern.search(text)
        if match:
            port = int(match.group(1))
            if _valid_port(port):
                return port
    return None


def _read_text(path: Path, max_bytes: int = 512_000) -> str:
    try:
        if not path.is_file() or path.stat().st_size > max_bytes:
            return ""
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _auto_port(preferred: int, root: Path, requested_port: int | None) -> int:
    if requested_port is not None:
        return requested_port
    try:
        return choose_available_port(preferred, project_dir=root)
    except PortAllocationError as exc:
        raise DetectionError(str(exc)) from exc


def _python_candidates(root: Path) -> Iterable[Path]:
    preferred = ["app.py", "main.py", "server.py", "web.py", "streamlit_app.py"]
    seen: set[Path] = set()
    for name in preferred:
        path = root / name
        if path.is_file():
            seen.add(path)
            yield path
    for path in sorted(root.glob("*.py")):
        if path not in seen:
            yield path


def _detect_python(root: Path, requested_port: int | None) -> DeployPlan | None:
    for path in _python_candidates(root):
        text = _read_text(path)
        if not text:
            continue
        module = path.stem

        streamlit = "import streamlit" in text or "from streamlit" in text
        if streamlit:
            port = _auto_port(_first_port(text) or 8501, root, requested_port)
            return DeployPlan(
                ["python", "-m", "streamlit", "run", path.name, "--server.address", "127.0.0.1", "--server.port", str(port)],
                port,
                "streamlit",
                path.name,
            )

        fastapi_match = re.search(r"(?m)^\s*([A-Za-z_]\w*)\s*=\s*FastAPI\s*\(", text)
        if fastapi_match:
            port = _auto_port(_first_port(text) or 8000, root, requested_port)
            app_var = fastapi_match.group(1)
            return DeployPlan(
                ["python", "-m", "uvicorn", f"{module}:{app_var}", "--host", "127.0.0.1", "--port", str(port)],
                port,
                "fastapi",
                path.name,
            )

        flask_match = re.search(r"(?m)^\s*([A-Za-z_]\w*)\s*=\s*Flask\s*\(", text)
        if flask_match:
            port = _auto_port(_first_port(text) or 8000, root, requested_port)
            app_var = flask_match.group(1)
            return DeployPlan(
                ["python", "-m", "flask", "--app", f"{module}:{app_var}", "run", "--host", "127.0.0.1", "--port", str(port)],
                port,
                "flask",
                path.name,
            )

        detected_port = _first_port(text)
        looks_like_http = any(
            marker in text
            for marker in (
                "HTTPServer(",
                "ThreadingHTTPServer(",
                "serve_forever(",
                "uvicorn.run(",
                "app.run(",
            )
        )
        if looks_like_http and detected_port is not None:
            if requested_port is not None and requested_port != detected_port:
                raise DetectionError(
                    f"{path.name} appears to use fixed port {detected_port}; cannot safely override it with {requested_port}."
                )
            return DeployPlan(["python", path.name], detected_port, "python-http", path.name)
    return None


def _detect_node(root: Path, requested_port: int | None) -> DeployPlan | None:
    package_path = root / "package.json"
    if not package_path.is_file():
        return None
    try:
        package = json.loads(package_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    scripts = package.get("scripts") or {}
    dependencies = {}
    dependencies.update(package.get("dependencies") or {})
    dependencies.update(package.get("devDependencies") or {})

    script_name = "start" if isinstance(scripts.get("start"), str) else "dev" if isinstance(scripts.get("dev"), str) else None
    if script_name is None:
        return None
    script = scripts[script_name]
    explicit_port = _first_port(script)

    if "vite" in dependencies or re.search(r"\bvite\b", script):
        if explicit_port is not None:
            if requested_port is not None and requested_port != explicit_port:
                raise DetectionError(
                    f"package.json Vite script appears to use fixed port {explicit_port}; cannot safely override it with {requested_port}."
                )
            port = explicit_port
            command = ["npm", "run", script_name]
            if "--host" not in script:
                command += ["--", "--host", "127.0.0.1"]
            return DeployPlan(command, port, "vite", "package.json")

        port = _auto_port(5173, root, requested_port)
        return DeployPlan(
            ["npm", "run", script_name, "--", "--host", "127.0.0.1", "--port", str(port)],
            port,
            "vite",
            "package.json",
        )

    if "next" in dependencies or re.search(r"\bnext\s+(?:dev|start)\b", script):
        if explicit_port is not None:
            if requested_port is not None and requested_port != explicit_port:
                raise DetectionError(
                    f"package.json Next.js script appears to use fixed port {explicit_port}; cannot safely override it with {requested_port}."
                )
            return DeployPlan(["npm", "run", script_name], explicit_port, "nextjs", "package.json")

        port = _auto_port(3000, root, requested_port)
        return DeployPlan(
            ["npm", "run", script_name, "--", "--hostname", "127.0.0.1", "--port", str(port)],
            port,
            "nextjs",
            "package.json",
        )

    if explicit_port is not None:
        if requested_port is not None and requested_port != explicit_port:
            raise DetectionError(
                f"package.json script appears to use fixed port {explicit_port}; cannot safely override it with {requested_port}."
            )
        return DeployPlan(["npm", "run", script_name], explicit_port, "node", "package.json")

    return None


def detect_deploy_plan(project_dir: Path | None = None, requested_port: int | None = None) -> DeployPlan:
    root = (project_dir or Path.cwd()).resolve()
    if requested_port is not None and not _valid_port(requested_port):
        raise DetectionError("port must be between 1 and 65535")

    existing = load_service_spec(root)
    if existing is not None and requested_port is None:
        return DeployPlan(
            list(existing["command"]),
            int(existing["port"]),
            "existing",
            ".minit/service.json",
        )

    node = _detect_node(root, requested_port)
    if node is not None:
        return node

    python = _detect_python(root, requested_port)
    if python is not None:
        return python

    if (root / "index.html").is_file():
        port = _auto_port(8000, root, requested_port)
        return DeployPlan(
            ["python", "-m", "http.server", str(port), "--bind", "127.0.0.1"],
            port,
            "static",
            "index.html",
        )

    raise DetectionError(
        "Could not safely detect how to run this project. Use `minit deploy --port <port> -- <command>` once; Minit will remember it."
    )


def infer_port_from_command(command: list[str], project_dir: Path | None = None) -> int | None:
    text = " ".join(command)
    port = _first_port(text)
    if port is not None:
        return port

    lowered = [part.lower() for part in command]
    if "http.server" in lowered:
        for part in command:
            if part.isdigit() and _valid_port(int(part)):
                return int(part)
    if "streamlit" in lowered:
        return 8501
    if "uvicorn" in lowered or "flask" in lowered:
        return 8000

    root = (project_dir or Path.cwd()).resolve()
    for part in command:
        if part.endswith(".py"):
            candidate = root / part
            detected = _first_port(_read_text(candidate))
            if detected is not None:
                return detected
    return None
