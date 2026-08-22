from pathlib import Path

import pytest

from minit.service import (
    build_service_spec,
    configure_local_service,
    load_service_spec,
    service_spec_path,
)


def test_service_spec_is_local_and_contains_no_secret_values(tmp_path: Path):
    spec = configure_local_service(
        ["python", "app.py"],
        8000,
        project_dir=tmp_path,
    )

    assert spec["command"] == ["python", "app.py"]
    assert spec["port"] == 8000
    assert spec["working_dir"] == str(tmp_path.resolve())
    assert spec["restart_policy"] == "on-failure"
    assert spec["environment_policy"] == "minimal"
    assert spec["autostart"] is False
    assert "env" not in spec
    assert "secrets" not in spec
    assert service_spec_path(tmp_path).exists()

    loaded = load_service_spec(tmp_path)
    assert loaded == spec


def test_service_spec_uses_same_persistent_app_identity(tmp_path: Path):
    first = configure_local_service(["python", "app.py"], 8000, tmp_path)
    second = build_service_spec(["python", "app.py"], 8000, tmp_path)

    assert first["app_id"] == second["app_id"]


def test_service_spec_rejects_invalid_port(tmp_path: Path):
    with pytest.raises(ValueError):
        build_service_spec(["python", "app.py"], 0, tmp_path)


def test_service_spec_rejects_unknown_restart_policy(tmp_path: Path):
    with pytest.raises(ValueError):
        build_service_spec(
            ["python", "app.py"],
            8000,
            tmp_path,
            restart_policy="sometimes",
        )


@pytest.mark.parametrize(
    "command",
    [
        ["python", "app.py", "--api-key=plaintext-secret"],
        ["python", "app.py", "--token", "plaintext-secret"],
        ["python", "app.py", "--password=plaintext-secret"],
    ],
)
def test_service_spec_rejects_obvious_secret_arguments(tmp_path: Path, command: list[str]):
    with pytest.raises(ValueError, match="secret argument"):
        build_service_spec(command, 8000, tmp_path)
