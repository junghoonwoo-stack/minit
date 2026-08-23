from __future__ import annotations

import ctypes
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


def _linux_plan(command: list[str], project_dir: Path) -> SandboxPlan:
    from minit.linux_sandbox_runner import landlock_abi

    abi = landlock_abi()
    if abi < 1:
        raise SandboxUnavailable(
            "Strict Linux sandbox requires a kernel with Landlock support."
        )
    root = _project_root(project_dir)
    _sandbox_home(root)
    _sandbox_temp(root)
    return SandboxPlan(
        command=[
            sys.executable,
            "-m",
            "minit.linux_sandbox_runner",
            "--project",
            str(root),
            "--",
            *command,
        ],
        backend=f"landlock-abi-{abi}",
        filesystem_policy="project-readonly-data-readwrite-home-denied-minit-hidden",
        network_policy="shared",
    )


def _sbpl_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _macos_profile(project_dir: Path) -> str:
    root = _project_root(project_dir)
    data = _data_dir(root)
    home = Path.home().resolve()
    _sandbox_home(root)
    _sandbox_temp(root)

    root_s = _sbpl_escape(str(root))
    data_s = _sbpl_escape(str(data))
    home_s = _sbpl_escape(str(home))
    minit_s = _sbpl_escape(str(root / MINIT_DIR))

    # Use the normal macOS execution environment and carve out the sensitive
    # filesystem boundary with explicit deny rules. `require-not` preserves the
    # app's own project/data exceptions without maintaining a brittle allowlist
    # of every framework/runtime file macOS may need to start Python/Node.
    if _path_within(root, home):
        home_read_deny = f'''(deny file-read*
  (require-all
    (subpath "{home_s}")
    (require-not (subpath "{root_s}"))))'''
    else:
        home_read_deny = f'(deny file-read* (subpath "{home_s}"))'

    return f'''(version 1)
(allow default)
{home_read_deny}
(deny file-read*
  (require-all
    (subpath "{minit_s}")
    (require-not (subpath "{data_s}"))))
(deny file-write*
  (require-all
    (subpath "{home_s}")
    (require-not (subpath "{data_s}"))))
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
        filesystem_policy="project-readonly-data-readwrite-home-denied-minit-hidden",
        network_policy="shared",
    )


def _fallback_appcontainer_sid(app_id: str) -> str:
    # Used only for deterministic non-Windows planning/tests. Real Windows uses
    # DeriveAppContainerSidFromAppContainerName so the SID is recognized by ACL APIs.
    digest = hashlib.sha256(app_id.encode("utf-8")).digest()
    parts = [int.from_bytes(digest[i : i + 4], "little") for i in range(0, 28, 4)]
    return "S-1-15-2-" + "-".join(str(part) for part in parts)


def windows_app_sid(app_id: str) -> str:
    if platform.system() != "Windows":
        return _fallback_appcontainer_sid(app_id)

    userenv = ctypes.WinDLL("userenv", use_last_error=True)
    advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    sid_ptr = ctypes.c_void_p()
    name = "minit." + app_id.lower().replace("-", "")
    derive = userenv.DeriveAppContainerSidFromAppContainerName
    derive.argtypes = [ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_void_p)]
    derive.restype = ctypes.c_long
    hr = int(derive(name, ctypes.byref(sid_ptr)))
    if hr != 0 or not sid_ptr.value:
        raise SandboxUnavailable(f"Could not derive Windows AppContainer SID (HRESULT 0x{hr & 0xFFFFFFFF:08x}).")

    string_ptr = ctypes.c_wchar_p()
    convert = advapi32.ConvertSidToStringSidW
    convert.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_wchar_p)]
    convert.restype = ctypes.c_int
    try:
        if not convert(sid_ptr, ctypes.byref(string_ptr)):
            raise SandboxUnavailable(
                f"Could not stringify Windows AppContainer SID (WinError {ctypes.get_last_error()})."
            )
        return str(string_ptr.value)
    finally:
        if string_ptr:
            kernel32.LocalFree(string_ptr)
        advapi32.FreeSid(sid_ptr)


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

    _run_icacls([
        str(root),
        "/grant:r",
        f"{user_sid}:(OI)(CI)F",
        f"{system_sid}:(OI)(CI)F",
        f"{sid_arg}:(OI)(CI)RX",
    ])
    _run_icacls([str(root), "/inheritance:r"])
    for broad_sid in ("*S-1-1-0", "*S-1-5-11", "*S-1-5-32-545"):
        _run_icacls([str(root), "/remove:g", broad_sid])

    # Remove the app SID from all manager-owned state before granting only
    # directory traversal and a writable mutable-data subtree.
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
