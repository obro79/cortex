from typer.testing import CliRunner

from cortex.cli.main import app


def test_cli_help(runner: CliRunner) -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0


def test_cli_doctor(runner: CliRunner) -> None:
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert "ok" in result.stdout


def test_cli_config_sanitizes_sensitive_values(
    runner: CliRunner, monkeypatch: object
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:password@localhost/db")
    result = runner.invoke(app, ["config"])
    assert result.exit_code == 0
    assert "[REDACTED]" in result.stdout
    assert "password" not in result.stdout
