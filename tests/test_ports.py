from pathlib import Path

import pytest

import minit.ports as ports
from minit.ports import PortAllocationError, choose_available_port, reserved_local_ports


def test_reserved_ports_exclude_current_project(tmp_path: Path, monkeypatch):
    current = tmp_path / "current"
    other = tmp_path / "other"
    current.mkdir()
    other.mkdir()
    monkeypatch.setattr(
        ports,
        "list_registered_apps",
        lambda: [
            {"project_dir": str(current), "port": 8000},
            {"project_dir": str(other), "port": 8001},
        ],
    )

    assert reserved_local_ports(current) == {8001}


def test_choose_available_port_skips_reserved_and_bound_ports(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(ports, "reserved_local_ports", lambda project_dir=None: {8000})
    monkeypatch.setattr(ports, "_port_bind_available", lambda port: port == 8002)

    assert choose_available_port(8000, tmp_path, scan=5) == 8002


def test_choose_available_port_fails_when_range_is_exhausted(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(ports, "reserved_local_ports", lambda project_dir=None: set())
    monkeypatch.setattr(ports, "_port_bind_available", lambda port: False)

    with pytest.raises(PortAllocationError, match="Could not find a free local port"):
        choose_available_port(8000, tmp_path, scan=3)
