from typer.testing import CliRunner

from cortex.workers.main import app, run_worker


async def test_run_noop_worker() -> None:
    assert await run_worker("noop") == 0


def test_worker_cli_noop(runner: CliRunner) -> None:
    result = runner.invoke(app, ["--role", "noop"])
    assert result.exit_code == 0
