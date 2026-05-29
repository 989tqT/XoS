"""``aletheia invoke`` — stdin JSON ingress and envelope stdout."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from aletheiacli.core.config import load_settings
from aletheiacli.core.emit import error_envelope, new_trace_id, success_envelope, write_stdout
from aletheiacli.core.executor import ExecutionError, execute
from aletheiacli.core.ingress import (
    IngressError,
    command_name,
    load_request_bytes,
    parse_agent_request,
)
from aletheiacli.models import ErrorItem

_COMMAND_UNKNOWN = "unknown"


def run_invoke(
    *,
    request_json: Path | None,
    pretty: bool,
) -> int:
    """Load request, validate, execute, emit envelope; return process exit code."""
    settings = load_settings()
    trace_command = _COMMAND_UNKNOWN
    trace_id = new_trace_id()

    try:
        raw = load_request_bytes(
            max_bytes=settings.max_stdin_bytes,
            request_json=request_json,
        )
        request = parse_agent_request(raw)
        trace_command = command_name(request)
        data = execute(request)
        envelope = success_envelope(command=trace_command, data=data, trace_id=trace_id)
    except IngressError as exc:
        envelope = error_envelope(
            command=trace_command,
            errors=[ErrorItem(code=exc.code, message=exc.message)],
            trace_id=trace_id,
        )
    except ExecutionError as exc:
        envelope = error_envelope(
            command=trace_command,
            errors=[ErrorItem(code=exc.code, message=exc.message)],
            trace_id=trace_id,
        )

    write_stdout(envelope, pretty=pretty)
    return 0 if envelope.ok else 1


def register_invoke(app: typer.Typer) -> None:
    """Register the ``invoke`` subcommand on ``app``."""

    @app.command("invoke")
    def invoke(
        request_json: Annotated[
            Path | None,
            typer.Option(
                "--request-json",
                help="Path to JSON request file (human debug; stdin is preferred for agents).",
                exists=False,
                readable=True,
                dir_okay=False,
                resolve_path=True,
            ),
        ] = None,
        pretty: Annotated[
            bool,
            typer.Option("--pretty", help="Pretty-print JSON stdout for human debugging."),
        ] = False,
    ) -> None:
        """Accept a JSON agent request on stdin and write a JSON envelope to stdout."""
        raise typer.Exit(code=run_invoke(request_json=request_json, pretty=pretty))
