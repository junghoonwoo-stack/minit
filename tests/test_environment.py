from pathlib import Path

from minit.environment import app_environment, minimal_environment
from minit.secrets import set_secret
from minit.state import create_manifest


class MemoryKeyStore:
    def __init__(self):
        self.values = {}

    def get(self, name: str):
        return self.values.get(name)

    def set(self, name: str, value: bytes):
        self.values[name] = value

    def delete(self, name: str):
        self.values.pop(name, None)


def test_minimal_environment_does_not_inherit_arbitrary_credentials():
    source = {
        "PATH": "/usr/bin",
        "HOME": "/home/user",
        "OPENAI_API_KEY": "must-not-leak",
        "AWS_SECRET_ACCESS_KEY": "must-not-leak",
        "DATABASE_URL": "must-not-leak",
    }

    env = minimal_environment(source)

    assert env["PATH"] == "/usr/bin"
    assert env["HOME"] == "/home/user"
    assert "OPENAI_API_KEY" not in env
    assert "AWS_SECRET_ACCESS_KEY" not in env
    assert "DATABASE_URL" not in env


def test_app_environment_contains_only_explicit_minit_secret(tmp_path: Path):
    store = MemoryKeyStore()
    manifest = create_manifest(tmp_path, name="demo")
    set_secret("OPENAI_API_KEY", "allowed-secret", tmp_path, store=store)
    spec = {
        "app_id": manifest["id"],
        "port": 8000,
    }
    source = {
        "PATH": "/usr/bin",
        "HOME": "/home/user",
        "AWS_SECRET_ACCESS_KEY": "must-not-leak",
    }

    env = app_environment(spec, tmp_path, store=store, source=source)

    assert env["OPENAI_API_KEY"] == "allowed-secret"
    assert "AWS_SECRET_ACCESS_KEY" not in env
    assert env["MINIT_APP_ID"] == manifest["id"]
    assert env["MINIT_RUNTIME"] == "local"
    assert env["MINIT_DATA_DIR"] == str(tmp_path / ".minit" / "data")
