import json
from pathlib import Path

import pytest

from minit.detection import DetectionError, detect_deploy_plan, infer_port_from_command
from minit.service import configure_local_service


def _keep_preferred_port(monkeypatch):
    monkeypatch.setattr(
        "minit.detection.choose_available_port",
        lambda preferred, project_dir=None: preferred,
    )


def test_detects_static_site(tmp_path: Path, monkeypatch):
    _keep_preferred_port(monkeypatch)
    (tmp_path / "index.html").write_text("<h1>Hello</h1>", encoding="utf-8")

    plan = detect_deploy_plan(tmp_path)

    assert plan.kind == "static"
    assert plan.port == 8000
    assert plan.command == ["python", "-m", "http.server", "8000", "--bind", "127.0.0.1"]


def test_detects_fastapi(tmp_path: Path, monkeypatch):
    _keep_preferred_port(monkeypatch)
    (tmp_path / "main.py").write_text(
        "from fastapi import FastAPI\napp = FastAPI()\n",
        encoding="utf-8",
    )

    plan = detect_deploy_plan(tmp_path)

    assert plan.kind == "fastapi"
    assert plan.port == 8000
    assert plan.command[-4:] == ["--host", "127.0.0.1", "--port", "8000"]
    assert "main:app" in plan.command


def test_detects_streamlit(tmp_path: Path):
    (tmp_path / "app.py").write_text("import streamlit as st\nst.title('Hi')\n", encoding="utf-8")

    plan = detect_deploy_plan(tmp_path, requested_port=8600)

    assert plan.kind == "streamlit"
    assert plan.port == 8600
    assert plan.command[-2:] == ["--server.port", "8600"]


def test_detects_vite_and_binds_locally(tmp_path: Path, monkeypatch):
    _keep_preferred_port(monkeypatch)
    (tmp_path / "package.json").write_text(
        json.dumps(
            {
                "scripts": {"dev": "vite"},
                "devDependencies": {"vite": "^7.0.0"},
            }
        ),
        encoding="utf-8",
    )

    plan = detect_deploy_plan(tmp_path)

    assert plan.kind == "vite"
    assert plan.port == 5173
    assert plan.command == [
        "npm", "run", "dev", "--", "--host", "127.0.0.1", "--port", "5173"
    ]


def test_auto_detected_static_site_uses_allocated_free_port(tmp_path: Path, monkeypatch):
    (tmp_path / "index.html").write_text("<h1>Hello</h1>", encoding="utf-8")
    monkeypatch.setattr(
        "minit.detection.choose_available_port",
        lambda preferred, project_dir=None: preferred + 2,
    )

    plan = detect_deploy_plan(tmp_path)

    assert plan.port == 8002
    assert plan.command == ["python", "-m", "http.server", "8002", "--bind", "127.0.0.1"]


def test_vite_explicit_script_port_is_not_silently_changed(tmp_path: Path):
    (tmp_path / "package.json").write_text(
        json.dumps(
            {
                "scripts": {"dev": "vite --port 4310"},
                "devDependencies": {"vite": "^7.0.0"},
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(DetectionError, match="fixed port 4310"):
        detect_deploy_plan(tmp_path, requested_port=4311)


def test_reuses_existing_service_configuration(tmp_path: Path):
    configure_local_service(["python", "server.py"], 9123, tmp_path)

    plan = detect_deploy_plan(tmp_path)

    assert plan.kind == "existing"
    assert plan.port == 9123
    assert plan.command == ["python", "server.py"]


def test_ambiguous_project_fails_closed(tmp_path: Path):
    (tmp_path / "notes.txt").write_text("not a web app", encoding="utf-8")

    with pytest.raises(DetectionError, match="Could not safely detect"):
        detect_deploy_plan(tmp_path)


def test_infers_port_from_explicit_python_command(tmp_path: Path):
    (tmp_path / "server.py").write_text(
        "from http.server import HTTPServer\nHTTPServer(('127.0.0.1', 9124), object)\n",
        encoding="utf-8",
    )

    assert infer_port_from_command(["python", "server.py"], tmp_path) == 9124
