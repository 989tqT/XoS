"""Write agent JSON envelopes to stdout."""

from __future__ import annotations

import sys
from uuid import UUID, uuid4

from xos import __version__
from xos.models import AgentResponse, ErrorItem, ResponseMeta


def new_trace_id() -> UUID:
    return uuid4()


def success_envelope(
    *,
    command: str,
    data: dict[str, object],
    trace_id: UUID | None = None,
    dry_run: bool = False,
) -> AgentResponse:
    return AgentResponse(
        ok=True,
        data=data,
        meta=ResponseMeta(
            trace_id=trace_id or new_trace_id(),
            command=command,
            dry_run=dry_run,
            version=__version__,
        ),
        errors=[],
    )


def error_envelope(
    *,
    command: str,
    errors: list[ErrorItem],
    trace_id: UUID | None = None,
    dry_run: bool = False,
) -> AgentResponse:
    return AgentResponse(
        ok=False,
        data={},
        meta=ResponseMeta(
            trace_id=trace_id or new_trace_id(),
            command=command,
            dry_run=dry_run,
            version=__version__,
        ),
        errors=errors,
    )


def write_stdout(envelope: AgentResponse, *, pretty: bool = False) -> None:
    """Serialize envelope to stdout (single line unless ``pretty``)."""
    text = envelope.model_dump_json(indent=2 if pretty else None)
    sys.stdout.write(text)
    sys.stdout.write("\n")
    sys.stdout.flush()
