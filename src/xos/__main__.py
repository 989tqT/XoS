"""CLI entry point: ``python -m xos`` or ``xos``."""

from __future__ import annotations

import typer

from xos.commands.invoke import register_invoke

app = typer.Typer(
    name="xos",
    help="Secure JSON-mediated CLI boundary for AI agents.",
    no_args_is_help=True,
    add_completion=False,
)

register_invoke(app)


@app.callback()
def main() -> None:
    """XoS root group."""


if __name__ == "__main__":
    app()
