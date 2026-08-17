from unittest.mock import patch

from typer.testing import CliRunner

from minit.cli import URL_RE, _cloudflared_asset, _detect_port, app

runner = CliRunner()


def test_trycloudflare_url_regex():
    line = "INF Your quick Tunnel has been created! Visit it at https://tiny-cat-123.trycloudflare.com"
    match = URL_RE.search(line)
    assert match
    assert match.group(0) == "https://tiny-cat-123.trycloudflare.com"


def test_detect_port_uses_common_ports_in_order():
    with patch("minit.cli._port_open", side_effect=lambda port: port == 8000):
        assert _detect_port() == 8000


def test_run_fails_cleanly_without_local_app():
    with patch("minit.cli._detect_port", return_value=None):
        result = runner.invoke(app, ["run"])
    assert result.exit_code == 1
    assert "No local web app found" in result.stdout


def test_doctor_says_networking_will_prepare_automatically():
    with patch("minit.cli._cloudflared_path", return_value=None), patch("minit.cli._detect_port", return_value=8501):
        result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert "prepare automatically" in result.stdout
    assert "8501" in result.stdout


def test_cloudflared_asset_for_macos_arm64():
    with patch("minit.cli.platform.system", return_value="Darwin"), patch("minit.cli.platform.machine", return_value="arm64"):
        assert _cloudflared_asset() == ("cloudflared-darwin-arm64.tgz", True)
