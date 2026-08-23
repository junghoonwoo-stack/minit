from __future__ import annotations

import hashlib
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from minit.private_fs import _windows_user_sid
from minit.state import MINIT_DIR


class SandboxUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class SandboxPlan:
    command: list[str]
    backend: str
    filesystem_policy: str
    network_policy: str


def _project_root(project_dir: Path) -> Path:
    return project_dir.resolve()


def _data_dir(project_dir: Path) -> Path:
    return _project_root(project_dir) / MINIT_DIR / "data"


def _sandbox_temp(project_dir: Path) -> Path:
    path = _data_dir(project_dir) / "tmp"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _sandbox_home(project_dir: Path) -> Path:
    path = _data_dir(project_dir) / "home"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _path_within(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _linux_target_dirs(root: Path, home: Path) -> list[str]:
    if not _path_within(root, home):
        return []
    dirs: list[str] = []
    current = home
    for part in root.relative_to(home).parts:
        current = current / part
        dirs.append(str(current))
    return dirs


def _linux_plan(command: list[str], project_dir: Path) -> SandboxPlan:
    bwrap = shutil.which("bwrap")
    if not bwrap:
        raise SandboxUnavailable(
            "Strict Linux sandbox requires bubblewrap (`bwrap`). Install the distro package named `bubblewrap`."
        )

    root = _project_root(project_dir)
    data = _data_dir(root)
    data.mkdir(parents=True, exist_ok=True)
    home = Path.home().resolve()
    sandbox_home = _sandbox_home(root)
    sandbox_tmp = _sandbox_temp(root)
    staged_project = "/run/minit-sandbox/project"
    staged_data = "/run/minit-sandbox/data"

    args = [
        bwrap,
        "--die-with-parent",
        "--new-session",
        "--ro-bind", "/", "/",
        "--proc", "/proc",
        "--dev", "/dev",
        # Capture the host project/data before hiding HOME and .minit. Later
        # binds use these already-open views as their sources.
        "--tmpfs", "/run",
        "--dir", "/run/minit-sandbox",
        "--ro-bind", str(root), staged_project,
        "--bind", str(data), staged_data,
    ]

    if _path_within(root, home):
        args += ["--tmpfs", str(home)]
        for directory in _linux_target_dirs(root, home):
            args += ["--dir", directory]
    args += ["--ro-bind", staged_project, str(root)]

    # The project view includes .minit, so mask it and re-expose only the app's
    # own mutable data. Control files, logs, wrapped keys, and backups disappear
    # from the app namespace.
    minit_dir = root / MINIT_DIR
    args += [
        "--tmpfs", str(minit_dir),
        "--dir", str(data),
        "--bind", staged_data, str(data),
        "--tmpfs", "/tmp",
        "--chdir", str(root),
        "--setenv", "HOME", str(sandbox_home),
        "--setenv", "TMPDIR", str(sandbox_tmp),
        "--setenv", "TMP", str(sandbox_tmp),
        "--setenv", "TEMP", str(sandbox_tmp),
        "--",
        *command,
    ]
    return SandboxPlan(
        command=args,
        backend="bubblewrap",
        filesystem_policy="project-readonly-data-readwrite-home-hidden-minit-hidden",
        network_policy="shared",
    )


def _sbpl_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _macos_project_read_rules(root: Path) -> list[str]:
    rules: list[str] = []
    for child in root.iterdir():
        if child.name == MINIT_DIR:
            continue
        kind = "subpath" if child.is_dir() else "literal"
        rules.append(f'  ({kind} "{_sbpl_escape(str(child.resolve()))}")')
    return rules


def _macos_profile(project_dir: Path) -> str:
    root = _project_root(project_dir)
    data = _data_dir(root)
    sandbox_home = _sandbox_home(root)
    sandbox_tmp = _sandbox_temp(root)

    readable = {
        "/System",
        "/usr",
        "/bin",
        "/sbin",
        "/Library",
        "/dev",
        "/private/etc",
        "/private/var/db",
        str(Path(sys.executable).resolve().parent),
        str(Path(sys.prefix).resolve()),
    }
    read_rules = [f'  (subpath "{_sbpl_escape(path)}")' for path in sorted(readable)]
    read_rules.extend(_macos_project_read_rules(root))
    read_rules.append(f'  (subpath "{_sbpl_escape(str(data))}")')
    rendered_reads = "\n".join(read_rules)
    return f'''(version 1)
(deny default)
(allow process*)
(allow signal (target self))
(allow sysctl-read)
(allow mach-lookup)
(allow ipc-posix-shm)
(allow network*)
(allow file-read-metadata)
(allow file-read*
{rendered_reads})
(allow file-write*
  (subpath "{_sbpl_escape(str(data))}")
  (subpath "{_sbpl_escape(str(sandbox_home))}")
  (subpath "{_sbpl_escape(str(sandbox_tmp))}")
  (subpath "/private/tmp"))
'''


def _macos_plan(command: list[str], project_dir: Path) -> SandboxPlan:
    sandbox_exec = shutil.which("sandbox-exec") or "/usr/bin/sandbox-exec"
    if not Path(sandbox_exec).exists():
        raise SandboxUnavailable(
            "Strict macOS sandbox requires the system `sandbox-exec` utility, which is unavailable on this machine."
        )
    profile = _macos_profile(project_dir)
    return SandboxPlan(
        command=[sandbox_exec, "-p", profile, *command],
        backend="sandbox-exec",
        filesystem_policy="project-readonly-data-readwrite-home-hidden-minit-hidden",
        network_policy="shared",
    )


def windows_app_sid(app_id: str) -> str:
    digest = hashlib.sha256(app_id.encode("utf-8")).digest()
    parts = [int.from_bytes(digest[i : i + 4], "little") for i in range(0, 16, 4)]
    return "S-1-5-21-" + "-".join(str(part) for part in parts)


def _run_icacls(args: list[str]) -> None:
    result = subprocess.run(
        ["icacls", *args],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise SandboxUnavailable(f"Windows ACL setup failed: {result.stderr.strip() or 'icacls error'}")


def prepare_windows_sandbox_acl(project_dir: Path, app_id: str) -> str:
    root = _project_root(project_dir)
    minit_dir = root / MINIT_DIR
    data = _data_dir(root)
    data.mkdir(parents=True, exist_ok=True)
    sid = windows_app_sid(app_id)
    sid_arg = f"*{sid}"
    user_sid = f"*{_windows_user_sid()}"
    system_sid = "*S-1-5-18"

    # Preserve the human owner before breaking broad inheritance. Applying the
    # root ACL non-recursively lets existing children inherit the new boundary
    # instead of being temporarily orphaned during a recursive inheritance pass.
    _run_icacls([str(root), "/grant:r", f"{user_sid}:(OI)(CI)F", f"{system_sid}:(OI)(CI)F", f"{sid_arg}:(OI)(CI)RX"])
    _run_icacls([str(root), "/inheritance:r"])
    for broad_sid in ("*S-1-1-0", "*S-1-5-11", "*S-1-5-32-545"):
        _run_icacls([str(root), "/remove:g", broad_sid])

    # Minit state is private to the manager. The app gets traverse on .minit
    # itself and Modify only inside .minit/data.
    if minit_dir.exists():
        _run_icacls([str(minit_dir), "/remove", sid_arg, "/T", "/C"])
        _run_icacls([str(minit_dir), "/grant", f"{user_sid}:(OI)(CI)F", f"{system_sid}:(OI)(CI)F"])
        _run_icacls([str(minit_dir), "/grant", f"{sid_arg}:(RX)"])
    _run_icacls([str(data), "/grant", f"{sid_arg}:(OI)(CI)M", "/T", "/C"])
    return sid


def _windows_plan(command: list[str], project_dir: Path, app_id: str) -> SandboxPlan:
    sid = prepare_windows_sandbox_acl(project_dir, app_id)
    root = _project_root(project_dir)
    return SandboxPlan(
        command=[
            sys.executable,
            "-m",
            "minit.windows_sandbox_runner",
            "--sid",
            sid,
            "--cwd",
            str(root),
            "--",
            *command,
        ],
        backend="windows-restricted-token",
        filesystem_policy="restricted-token-project-readonly-data-readwrite-minit-hidden",
        network_policy="shared",
    )


def strict_sandbox_plan(spec: dict, project_dir: Path) -> SandboxPlan:
    command = [str(part) for part in spec["command"]]
    system = platform.system()
    if system == "Linux":
        return _linux_plan(command, project_dir)
    if system == "Darwin":
        return _macos_plan(command, project_dir)
    if system == "Windows":
        return _windows_plan(command, project_dir, str(spec["app_id"]))
    raise SandboxUnavailable(f"Strict sandbox is not implemented on {system}.")


def sandbox_plan(spec: dict, project_dir: Path) -> SandboxPlan:
    policy = spec.get("sandbox_policy", "legacy-unsandboxed")
    if policy == "strict":
        return strict_sandbox_plan(spec, project_dir)
    if policy == "legacy-unsandboxed":
        return SandboxPlan(
            command=[str(part) for part in spec["command"]],
            backend="none",
            filesystem_policy="user-account-authority",
            network_policy="shared",
        )
    raise SandboxUnavailable(f"Unknown sandbox policy: {policy}")
