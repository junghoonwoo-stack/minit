from __future__ import annotations

import os
import platform
import plistlib
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from minit.private_fs import atomic_write_bytes, atomic_write_text, ensure_private_dir
from minit.service import load_service_spec, save_service_spec


class AutostartUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class AutostartInfo:
    platform: str
    identifier: str
    path: Path | None
    installed: bool


def _project_root(project_dir: Path | None = None) -> Path:
    return (project_dir or Path.cwd()).resolve()


def _spec(project_dir: Path) -> dict:
    spec = load_service_spec(project_dir)
    if spec is None:
        raise AutostartUnavailable("No local service is configured. Run `minit deploy` first.")
    return spec


def _identifier(app_id: str) -> str:
    return app_id.lower().replace("-", "")


def _systemd_quote(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def linux_unit_name(app_id: str) -> str:
    return f"minit-{_identifier(app_id)}.service"


def linux_unit_path(app_id: str, home: Path | None = None) -> Path:
    root = home or Path.home()
    return root / ".config" / "systemd" / "user" / linux_unit_name(app_id)


def render_linux_unit(project_dir: Path, python_executable: str | None = None) -> str:
    root = project_dir.resolve()
    spec = _spec(root)
    executable = python_executable or sys.executable
    return (
        "[Unit]\n"
        f"Description=Minit local app {spec['app_id']}\n"
        "After=default.target\n\n"
        "[Service]\n"
        "Type=simple\n"
        f"ExecStart={_systemd_quote(executable)} -m minit.supervisor {_systemd_quote(str(root))}\n"
        "Restart=on-failure\n"
        "RestartSec=2\n\n"
        "[Install]\n"
        "WantedBy=default.target\n"
    )


def macos_label(app_id: str) -> str:
    return f"app.minit.{_identifier(app_id)}"


def macos_plist_path(app_id: str, home: Path | None = None) -> Path:
    root = home or Path.home()
    return root / "Library" / "LaunchAgents" / f"{macos_label(app_id)}.plist"


def render_macos_plist(project_dir: Path, python_executable: str | None = None) -> bytes:
    root = project_dir.resolve()
    spec = _spec(root)
    executable = python_executable or sys.executable
    payload = {
        "Label": macos_label(spec["app_id"]),
        "ProgramArguments": [executable, "-m", "minit.supervisor", str(root)],
        "RunAtLoad": True,
        "KeepAlive": {"SuccessfulExit": False},
        "WorkingDirectory": str(root),
    }
    return plistlib.dumps(payload, fmt=plistlib.FMT_XML, sort_keys=True)


def windows_task_name(app_id: str) -> str:
    return f"Minit-{_identifier(app_id)}"


def windows_supervisor_command(project_dir: Path, python_executable: str | None = None) -> str:
    root = project_dir.resolve()
    _spec(root)
    executable_path = Path(python_executable or sys.executable)
    pythonw = executable_path.with_name("pythonw.exe")
    executable = str(pythonw if pythonw.exists() else executable_path)
    return subprocess.list2cmdline([executable, "-m", "minit.supervisor", str(root)])


def autostart_info(project_dir: Path | None = None, system: str | None = None) -> AutostartInfo:
    root = _project_root(project_dir)
    spec = _spec(root)
    platform_name = system or platform.system()

    if platform_name == "Linux":
        path = linux_unit_path(spec["app_id"])
        return AutostartInfo(platform_name, linux_unit_name(spec["app_id"]), path, path.exists())
    if platform_name == "Darwin":
        path = macos_plist_path(spec["app_id"])
        return AutostartInfo(platform_name, macos_label(spec["app_id"]), path, path.exists())
    if platform_name == "Windows":
        return AutostartInfo(platform_name, windows_task_name(spec["app_id"]), None, bool(spec.get("autostart")))

    raise AutostartUnavailable(f"Autostart is not supported on {platform_name} yet.")


def _mark_autostart(project_dir: Path, enabled: bool) -> None:
    spec = _spec(project_dir)
    spec["autostart"] = enabled
    save_service_spec(spec, project_dir)


def enable_autostart(project_dir: Path | None = None) -> AutostartInfo:
    root = _project_root(project_dir)
    spec = _spec(root)
    system = platform.system()

    if system == "Linux":
        if not shutil_which("systemctl"):
            raise AutostartUnavailable("systemctl is not available for user-level autostart.")
        path = linux_unit_path(spec["app_id"])
        ensure_private_dir(path.parent)
        atomic_write_text(path, render_linux_unit(root))
        subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
        subprocess.run(["systemctl", "--user", "enable", path.name], check=True)
        _mark_autostart(root, True)
        return AutostartInfo(system, path.name, path, True)

    if system == "Darwin":
        path = macos_plist_path(spec["app_id"])
        ensure_private_dir(path.parent)
        atomic_write_bytes(path, render_macos_plist(root))
        _mark_autostart(root, True)
        return AutostartInfo(system, macos_label(spec["app_id"]), path, True)

    if system == "Windows":
        command = windows_supervisor_command(root)
        task_name = windows_task_name(spec["app_id"])
        subprocess.run(
            ["schtasks", "/Create", "/F", "/SC", "ONLOGON", "/TN", task_name, "/TR", command],
            check=True,
        )
        _mark_autostart(root, True)
        return AutostartInfo(system, task_name, None, True)

    raise AutostartUnavailable(f"Autostart is not supported on {system} yet.")


def disable_autostart(project_dir: Path | None = None) -> AutostartInfo:
    root = _project_root(project_dir)
    spec = _spec(root)
    system = platform.system()

    if system == "Linux":
        path = linux_unit_path(spec["app_id"])
        if shutil_which("systemctl"):
            subprocess.run(["systemctl", "--user", "disable", path.name], check=False)
        path.unlink(missing_ok=True)
        if shutil_which("systemctl"):
            subprocess.run(["systemctl", "--user", "daemon-reload"], check=False)
        _mark_autostart(root, False)
        return AutostartInfo(system, path.name, path, False)

    if system == "Darwin":
        path = macos_plist_path(spec["app_id"])
        path.unlink(missing_ok=True)
        _mark_autostart(root, False)
        return AutostartInfo(system, macos_label(spec["app_id"]), path, False)

    if system == "Windows":
        task_name = windows_task_name(spec["app_id"])
        subprocess.run(["schtasks", "/Delete", "/F", "/TN", task_name], check=False)
        _mark_autostart(root, False)
        return AutostartInfo(system, task_name, None, False)

    raise AutostartUnavailable(f"Autostart is not supported on {system} yet.")


def shutil_which(command: str) -> str | None:
    import shutil

    return shutil.which(command)
