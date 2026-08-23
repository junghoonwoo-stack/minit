from __future__ import annotations

import argparse
import ctypes
import os
import sys
from pathlib import Path

# Landlock syscalls are assigned from the generic Linux syscall table on the
# architectures Minit supports in CI (x86_64/aarch64).
SYS_LANDLOCK_CREATE_RULESET = 444
SYS_LANDLOCK_ADD_RULE = 445
SYS_LANDLOCK_RESTRICT_SELF = 446
LANDLOCK_CREATE_RULESET_VERSION = 1
LANDLOCK_RULE_PATH_BENEATH = 1
PR_SET_NO_NEW_PRIVS = 38

LANDLOCK_ACCESS_FS_EXECUTE = 1 << 0
LANDLOCK_ACCESS_FS_WRITE_FILE = 1 << 1
LANDLOCK_ACCESS_FS_READ_FILE = 1 << 2
LANDLOCK_ACCESS_FS_READ_DIR = 1 << 3
LANDLOCK_ACCESS_FS_REMOVE_DIR = 1 << 4
LANDLOCK_ACCESS_FS_REMOVE_FILE = 1 << 5
LANDLOCK_ACCESS_FS_MAKE_CHAR = 1 << 6
LANDLOCK_ACCESS_FS_MAKE_DIR = 1 << 7
LANDLOCK_ACCESS_FS_MAKE_REG = 1 << 8
LANDLOCK_ACCESS_FS_MAKE_SOCK = 1 << 9
LANDLOCK_ACCESS_FS_MAKE_FIFO = 1 << 10
LANDLOCK_ACCESS_FS_MAKE_BLOCK = 1 << 11
LANDLOCK_ACCESS_FS_MAKE_SYM = 1 << 12
LANDLOCK_ACCESS_FS_REFER = 1 << 13
LANDLOCK_ACCESS_FS_TRUNCATE = 1 << 14

READ_EXEC_DIR = (
    LANDLOCK_ACCESS_FS_EXECUTE
    | LANDLOCK_ACCESS_FS_READ_FILE
    | LANDLOCK_ACCESS_FS_READ_DIR
)
READ_EXEC_FILE = LANDLOCK_ACCESS_FS_EXECUTE | LANDLOCK_ACCESS_FS_READ_FILE
WRITE_BASIC = (
    LANDLOCK_ACCESS_FS_WRITE_FILE
    | LANDLOCK_ACCESS_FS_REMOVE_DIR
    | LANDLOCK_ACCESS_FS_REMOVE_FILE
    | LANDLOCK_ACCESS_FS_MAKE_CHAR
    | LANDLOCK_ACCESS_FS_MAKE_DIR
    | LANDLOCK_ACCESS_FS_MAKE_REG
    | LANDLOCK_ACCESS_FS_MAKE_SOCK
    | LANDLOCK_ACCESS_FS_MAKE_FIFO
    | LANDLOCK_ACCESS_FS_MAKE_BLOCK
    | LANDLOCK_ACCESS_FS_MAKE_SYM
)

libc = ctypes.CDLL(None, use_errno=True)


class RulesetAttr(ctypes.Structure):
    _fields_ = [("handled_access_fs", ctypes.c_uint64)]


class PathBeneathAttr(ctypes.Structure):
    _fields_ = [
        ("allowed_access", ctypes.c_uint64),
        ("parent_fd", ctypes.c_int32),
    ]


def _syscall(number: int, *args: object) -> int:
    result = int(libc.syscall(number, *args))
    if result < 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error))
    return result


def landlock_abi() -> int:
    try:
        return _syscall(
            SYS_LANDLOCK_CREATE_RULESET,
            ctypes.c_void_p(),
            ctypes.c_size_t(0),
            ctypes.c_uint32(LANDLOCK_CREATE_RULESET_VERSION),
        )
    except OSError:
        return 0


def _handled_access(abi: int) -> int:
    access = READ_EXEC_DIR | WRITE_BASIC
    if abi >= 2:
        access |= LANDLOCK_ACCESS_FS_REFER
    if abi >= 3:
        access |= LANDLOCK_ACCESS_FS_TRUNCATE
    return access


def _write_access(abi: int) -> int:
    access = WRITE_BASIC
    if abi >= 2:
        access |= LANDLOCK_ACCESS_FS_REFER
    if abi >= 3:
        access |= LANDLOCK_ACCESS_FS_TRUNCATE
    return access


def _access_for_path(path: Path, requested: int) -> int:
    """Strip Landlock rights that are invalid for a regular-file parent_fd."""
    if path.is_dir():
        return requested
    valid_file_access = (
        LANDLOCK_ACCESS_FS_EXECUTE
        | LANDLOCK_ACCESS_FS_WRITE_FILE
        | LANDLOCK_ACCESS_FS_READ_FILE
        | LANDLOCK_ACCESS_FS_TRUNCATE
    )
    return requested & valid_file_access


def _add_path_rule(ruleset_fd: int, path: Path, access: int) -> None:
    if not path.exists():
        return
    allowed = _access_for_path(path, access)
    if not allowed:
        return
    flags = getattr(os, "O_PATH", os.O_RDONLY) | os.O_CLOEXEC
    fd = os.open(str(path), flags)
    try:
        attr = PathBeneathAttr(allowed_access=allowed, parent_fd=fd)
        _syscall(
            SYS_LANDLOCK_ADD_RULE,
            ctypes.c_int(ruleset_fd),
            ctypes.c_int(LANDLOCK_RULE_PATH_BENEATH),
            ctypes.byref(attr),
            ctypes.c_uint32(0),
        )
    finally:
        os.close(fd)


def _project_read_paths(root: Path) -> list[Path]:
    return [child for child in root.iterdir() if child.name != ".minit"]


def apply_landlock(project_dir: Path) -> int:
    abi = landlock_abi()
    if abi < 1:
        raise RuntimeError("Linux Landlock is unavailable on this kernel.")

    handled = _handled_access(abi)
    attr = RulesetAttr(handled_access_fs=handled)
    ruleset_fd = _syscall(
        SYS_LANDLOCK_CREATE_RULESET,
        ctypes.byref(attr),
        ctypes.sizeof(attr),
        ctypes.c_uint32(0),
    )
    try:
        root = project_dir.resolve()
        data = root / ".minit" / "data"
        data.mkdir(parents=True, exist_ok=True)

        # Runtime and system libraries: read/execute only. Landlock handles only
        # filesystem access; networking remains governed by the explicit
        # Minit network policy.
        runtime_roots = [
            Path("/usr"),
            Path("/bin"),
            Path("/sbin"),
            Path("/lib"),
            Path("/lib64"),
            Path("/etc"),
            Path("/dev"),
            Path("/proc"),
            Path("/sys"),
            Path(sys.executable).resolve().parent,
            Path(sys.prefix).resolve(),
        ]
        seen: set[str] = set()
        for path in [*runtime_roots, *_project_read_paths(root)]:
            key = str(path.resolve()) if path.exists() else str(path)
            if key in seen:
                continue
            seen.add(key)
            access = READ_EXEC_DIR if path.is_dir() else READ_EXEC_FILE
            _add_path_rule(ruleset_fd, path, access)

        _add_path_rule(ruleset_fd, data, READ_EXEC_DIR | _write_access(abi))

        if libc.prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) != 0:
            error = ctypes.get_errno()
            raise OSError(error, os.strerror(error))
        _syscall(SYS_LANDLOCK_RESTRICT_SELF, ctypes.c_int(ruleset_fd), ctypes.c_uint32(0))
        return abi
    finally:
        os.close(ruleset_fd)


def main() -> int:
    if sys.platform != "linux":
        print("linux_sandbox_runner is Linux-only", file=sys.stderr)
        return 2
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = list(args.command)
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        parser.error("missing command after --")
    try:
        apply_landlock(Path(args.project))
        os.execvpe(command[0], command, os.environ)
    except Exception as exc:
        print(f"Minit Linux sandbox failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 126
    return 126


if __name__ == "__main__":
    raise SystemExit(main())
