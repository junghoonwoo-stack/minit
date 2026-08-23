from __future__ import annotations

import argparse
import ctypes
import os
import subprocess
import sys
from ctypes import wintypes


if os.name == "nt":
    advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    TOKEN_ASSIGN_PRIMARY = 0x0001
    TOKEN_DUPLICATE = 0x0002
    TOKEN_QUERY = 0x0008
    DISABLE_MAX_PRIVILEGE = 0x1
    CREATE_UNICODE_ENVIRONMENT = 0x00000400
    INFINITE = 0xFFFFFFFF
    STARTF_USESTDHANDLES = 0x00000100
    STD_INPUT_HANDLE = -10
    STD_OUTPUT_HANDLE = -11
    STD_ERROR_HANDLE = -12

    class SID_AND_ATTRIBUTES(ctypes.Structure):
        _fields_ = [("Sid", wintypes.LPVOID), ("Attributes", wintypes.DWORD)]

    class STARTUPINFOW(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD),
            ("lpReserved", wintypes.LPWSTR),
            ("lpDesktop", wintypes.LPWSTR),
            ("lpTitle", wintypes.LPWSTR),
            ("dwX", wintypes.DWORD),
            ("dwY", wintypes.DWORD),
            ("dwXSize", wintypes.DWORD),
            ("dwYSize", wintypes.DWORD),
            ("dwXCountChars", wintypes.DWORD),
            ("dwYCountChars", wintypes.DWORD),
            ("dwFillAttribute", wintypes.DWORD),
            ("dwFlags", wintypes.DWORD),
            ("wShowWindow", wintypes.WORD),
            ("cbReserved2", wintypes.WORD),
            ("lpReserved2", ctypes.POINTER(ctypes.c_byte)),
            ("hStdInput", wintypes.HANDLE),
            ("hStdOutput", wintypes.HANDLE),
            ("hStdError", wintypes.HANDLE),
        ]

    class PROCESS_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("hProcess", wintypes.HANDLE),
            ("hThread", wintypes.HANDLE),
            ("dwProcessId", wintypes.DWORD),
            ("dwThreadId", wintypes.DWORD),
        ]


def _raise_last_error(action: str) -> None:
    code = ctypes.get_last_error()
    raise OSError(code, f"{action} failed with WinError {code}")


def _sid_from_string(value: str) -> wintypes.LPVOID:
    sid = wintypes.LPVOID()
    if not advapi32.ConvertStringSidToSidW(wintypes.LPCWSTR(value), ctypes.byref(sid)):
        _raise_last_error("ConvertStringSidToSidW")
    return sid


def _environment_block() -> ctypes.Array:
    # Windows requires a sorted double-NUL-terminated Unicode environment block.
    items = sorted(os.environ.items(), key=lambda item: item[0].upper())
    text = "\0".join(f"{key}={value}" for key, value in items) + "\0\0"
    return ctypes.create_unicode_buffer(text)


def _create_restricted_token(app_sid: str) -> wintypes.HANDLE:
    current = wintypes.HANDLE()
    rights = TOKEN_ASSIGN_PRIMARY | TOKEN_DUPLICATE | TOKEN_QUERY
    if not advapi32.OpenProcessToken(kernel32.GetCurrentProcess(), rights, ctypes.byref(current)):
        _raise_last_error("OpenProcessToken")

    allocated: list[wintypes.LPVOID] = []
    try:
        # BUILTIN\Users keeps access to normal Windows/program files. The
        # app-specific restricting SID is separately ACLed onto the project.
        sid_values = ["S-1-5-32-545", app_sid]
        sid_array = (SID_AND_ATTRIBUTES * len(sid_values))()
        for index, value in enumerate(sid_values):
            sid = _sid_from_string(value)
            allocated.append(sid)
            sid_array[index].Sid = sid
            sid_array[index].Attributes = 0

        restricted = wintypes.HANDLE()
        ok = advapi32.CreateRestrictedToken(
            current,
            DISABLE_MAX_PRIVILEGE,
            0,
            None,
            0,
            None,
            len(sid_values),
            sid_array,
            ctypes.byref(restricted),
        )
        if not ok:
            _raise_last_error("CreateRestrictedToken")
        return restricted
    finally:
        kernel32.CloseHandle(current)
        for sid in allocated:
            kernel32.LocalFree(sid)


def _run_restricted(app_sid: str, cwd: str, command: list[str]) -> int:
    token = _create_restricted_token(app_sid)
    try:
        command_line = ctypes.create_unicode_buffer(subprocess.list2cmdline(command))
        env_block = _environment_block()
        startup = STARTUPINFOW()
        startup.cb = ctypes.sizeof(STARTUPINFOW)
        startup.dwFlags = STARTF_USESTDHANDLES
        startup.hStdInput = kernel32.GetStdHandle(STD_INPUT_HANDLE)
        startup.hStdOutput = kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
        startup.hStdError = kernel32.GetStdHandle(STD_ERROR_HANDLE)
        info = PROCESS_INFORMATION()

        ok = advapi32.CreateProcessAsUserW(
            token,
            None,
            command_line,
            None,
            None,
            True,
            CREATE_UNICODE_ENVIRONMENT,
            ctypes.byref(env_block),
            cwd,
            ctypes.byref(startup),
            ctypes.byref(info),
        )
        if not ok:
            _raise_last_error("CreateProcessAsUserW")

        kernel32.CloseHandle(info.hThread)
        try:
            kernel32.WaitForSingleObject(info.hProcess, INFINITE)
            exit_code = wintypes.DWORD()
            if not kernel32.GetExitCodeProcess(info.hProcess, ctypes.byref(exit_code)):
                _raise_last_error("GetExitCodeProcess")
            return int(exit_code.value)
        finally:
            kernel32.CloseHandle(info.hProcess)
    finally:
        kernel32.CloseHandle(token)


def main() -> int:
    if os.name != "nt":
        print("windows_sandbox_runner is Windows-only", file=sys.stderr)
        return 2

    parser = argparse.ArgumentParser()
    parser.add_argument("--sid", required=True)
    parser.add_argument("--cwd", required=True)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = list(args.command)
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        parser.error("missing command after --")
    try:
        return _run_restricted(args.sid, args.cwd, command)
    except Exception as exc:
        print(f"Minit Windows sandbox failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 126


if __name__ == "__main__":
    raise SystemExit(main())
