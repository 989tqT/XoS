"""CLI entry point: ``python -m aletheiacli`` or ``aletheia``."""

from __future__ import annotations

import typer

from aletheiacli.commands.invoke import register_invoke

app = typer.Typer(
    name="aletheia",
    help="Secure JSON-mediated CLI boundary for AI agents.",
    no_args_is_help=True,
    add_completion=False,
)

register_invoke(app)


@app.callback()
def main() -> None:
    """AletheiaCLI root group."""


if __name__ == "__main__":
    app()
