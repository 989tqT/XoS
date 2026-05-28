# JSON I/O Envelope

All agent-facing output on **stdout** is a single JSON document.

## Response shape

```json
{
  "ok": true,
  "data": {},
  "meta": {
    "trace_id": "550e8400-e29b-41d4-a716-446655440000",
    "command": "health",
    "dry_run": false,
    "version": "0.0.1"
  },
  "errors": []
}
```

| Field | Type | Notes |
|-------|------|--------|
| `ok` | `bool` | `false` when validation or execution failed |
| `data` | `object` | Command-specific payload |
| `meta.trace_id` | UUID | Correlate with masked internal logs |
| `meta.command` | `string` | e.g. `health`, `read_log` |
| `meta.dry_run` | `bool` | Reserved for plan-only mode (future) |
| `errors` | `array` | `{ "code", "message" }` — messages masked at output (Phase 1.4+) |

## Request shape (discriminated by `op`)

| `op` | Model | Ingress | Execution |
|------|--------|---------|-----------|
| `health` | `HealthRequest` | Done | Planned (Phase 1.3) |
| `read_log` | `ReadLogRequest` | Done | Planned (Phase 1.4) |

Implementation: `src/aletheiacli/models/`.

## Ingress (`aletheia invoke`)

```bash
echo '{"op":"health"}' | aletheia invoke
aletheia invoke --request-json ./request.json
aletheia invoke --pretty
```

- **Primary:** JSON on **stdin**; empty TTY without `--request-json` → `EMPTY_PAYLOAD`.
- **Limit:** `ALETHEIA_MAX_STDIN_BYTES` (default `1048576`).
- **Errors:** `ok: false`, structured `errors[].code`; process exit code `1`.

### Interim success payload (until Phase 1.3)

After validation, `data` currently includes:

```json
{
  "accepted": true,
  "op": "health",
  "execution": "pending"
}
```

This confirms ingress only; it is **not** the final `health` or `read_log` result.
