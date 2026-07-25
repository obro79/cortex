import json

import typer

from cortex.config import Settings
from cortex.observability.logging import setup_logging

app = typer.Typer(help="Cortex command line tools")


@app.callback()
def main() -> None:
    """Cortex CLI."""


@app.command()
def doctor() -> None:
    settings = Settings()
    setup_logging(settings.cortex_log_level)
    typer.echo("ok")


@app.command("config")
def config_command() -> None:
    settings = Settings()
    typer.echo(json.dumps(settings.sanitized_dict(), indent=2, sort_keys=True))
