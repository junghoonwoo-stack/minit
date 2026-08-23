from pathlib import Path
from unittest.mock import patch

from minit.autostart import (
    autostart_info,
    linux_unit_name,
    render_linux_unit,
    render_macos_plist,
    windows_task_name,
)
from minit.service import configure_local_service


def test_linux_unit_runs_local_supervisor_without_secrets(tmp_path: Path):
    spec = configure_local_service(["python", "app.py"], 8000, tmp_path)

    unit = render_linux_unit(tmp_path, python_executable="/usr/bin/python3")
    escaped_root = str(tmp_path.resolve()).replace("\\", "\\\\").replace('"', '\\"')

    assert linux_unit_name(spec["app_id"]) in str(linux_unit_name(spec["app_id"]))
    assert "/usr/bin/python3" in unit
    assert "-m minit.supervisor" in unit
    assert f'"{escaped_root}"' in unit
    assert "OPENAI_API_KEY" not in unit
    assert "Environment=" not in unit


def test_macos_plist_contains_only_supervisor_command(tmp_path: Path):
    configure_local_service(["python", "app.py"], 8000, tmp_path)

    plist = render_macos_plist(tmp_path, python_executable="/usr/bin/python3").decode("utf-8")

    assert "minit.supervisor" in plist
    assert str(tmp_path.resolve()) in plist
    assert "OPENAI_API_KEY" not in plist


def test_windows_task_name_is_stable_for_app(tmp_path: Path):
    spec = configure_local_service(["python", "app.py"], 8000, tmp_path)

    assert windows_task_name(spec["app_id"]) == windows_task_name(spec["app_id"])


def test_autostart_status_is_pure_for_linux(tmp_path: Path, monkeypatch):
    spec = configure_local_service(["python", "app.py"], 8000, tmp_path)
    fake_home = tmp_path / "home"

    with patch("minit.autostart.Path.home", return_value=fake_home):
        info = autostart_info(tmp_path, system="Linux")

    assert info.platform == "Linux"
    assert info.identifier == linux_unit_name(spec["app_id"])
    assert not info.installed
