from __future__ import annotations

import os
from pathlib import Path
from typing import Mapping

from minit.key_store import KeyStore
from minit.secrets import get_all_secrets
from minit.state import MINIT_DIR

# Keep process startup usable across supported OSes without inheriting arbitrary
# shell/application credentials. Additions to this set should be reviewed as a
# security-boundary change.
SAFE_BASE_ENV_KEYS = {
    "PATH",
    "HOME",
    "USER",
    "LOGNAME",
    "USERPROFILE",
    # Python normalizes Windows environment-variable keys to uppercase. Windows
    # system components (including Winsock providers) can require SYSTEMROOT.
    "SYSTEMROOT",
    "WINDIR",
    "COMSPEC",
    "PATHEXT",
    "APPDATA",
    "LOCALAPPDATA",
    "TEMP",
    "TMP",
    "TMPDIR",
    "LANG",
    "LC_ALL",
    "LC_CTYPE",
    "TZ",
    # Common desktop Linux keyring/session plumbing. These identify the local
    # session but are not application secrets.
    "XDG_RUNTIME_DIR",
    "DBUS_SESSION_BUS_ADDRESS",
    "DISPLAY",
    "WAYLAND_DISPLAY",
}


def minimal_environment(source: Mapping[str, str] | None = None) -> dict[str, str]:
    source_env = source or os.environ
    return {
        key: value
        for key, value in source_env.items()
        if key in SAFE_BASE_ENV_KEYS
    }


def supervisor_environment(source: Mapping[str, str] | None = None) -> dict[str, str]:
    env = minimal_environment(source)
    env["MINIT_INTERNAL_SUPERVISOR"] = "1"
    return env


def app_data_dir(project_dir: Path | None = None) -> Path:
    root = (project_dir or Path.cwd()).resolve()
    return root / MINIT_DIR / "data"


def app_environment(
    spec: dict,
    project_dir: Path | None = None,
    *,
    store: KeyStore | None = None,
    source: Mapping[str, str] | None = None,
) -> dict[str, str]:
    root = (project_dir or Path.cwd()).resolve()
    data_dir = app_data_dir(root)
    data_dir.mkdir(parents=True, exist_ok=True)

    env = minimal_environment(source)
    env.update(
        {
            "MINIT_APP_ID": str(spec["app_id"]),
            "MINIT_RUNTIME": "local",
            "MINIT_DATA_DIR": str(data_dir),
        }
    )
    env.update(get_all_secrets(root, store=store))
    return env
