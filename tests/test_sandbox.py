from pathlib import Path

import pytest

from minit.sandbox import SandboxUnavailable, sandbox_plan, windows_app_sid


def test_windows_app_sid_is_stable_and_app_specific():
    a1 = windows_app_sid("11111111-1111-1111-1111-111111111111")
    a2 = windows_app_sid("11111111-1111-1111-1111-111111111111")
    b = windows_app_sid("22222222-2222-2222-2222-222222222222")
    assert a1 == a2
    assert a1 != b
    assert a1.startswith("S-1-5-21-")


def test_legacy_service_is_explicitly_unsandboxed(tmp_path: Path):
    spec = {
        "app_id": "legacy",
        "command": ["python", "app.py"],
        "sandbox_policy": "legacy-unsandboxed",
    }
    plan = sandbox_plan(spec, tmp_path)
    assert plan.command == ["python", "app.py"]
    assert plan.backend == "none"
    assert plan.filesystem_policy == "user-account-authority"
    assert plan.network_policy == "shared"


def test_unknown_sandbox_policy_fails_closed(tmp_path: Path):
    spec = {
        "app_id": "bad",
        "command": ["python", "app.py"],
        "sandbox_policy": "guess",
    }
    with pytest.raises(SandboxUnavailable):
        sandbox_plan(spec, tmp_path)
