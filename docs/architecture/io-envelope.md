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
| `meta.command` | `string` | e.g. `health`, `read_log`, `write_file` |
| `meta.dry_run` | `bool` | Reserved for plan-only mode (future) |
| `errors` | `array` | `{ "code", "message" }` — messages masked at output (Phase 1.4+) |

## Request shape (discriminated by `op`)

| `op` | Model | Ingress | Execution |
|------|--------|---------|-----------|
| `health` | `HealthRequest` | Done | Done |
| `read_log` | `ReadLogRequest` | Done | Done (Phase 1.4) |
| `write_file` | `WriteFileRequest` | Done | Done (Phase 1.5) |

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

### `health` success `data` (Phase 1.3)

```json
{
  "status": "ok",
  "platform": "Windows",
  "platform_release": "11",
  "platform_version": "...",
  "python_version": "3.12.3",
  "python_implementation": "CPython",
  "executable": "...",
  "cli_version": "0.0.1"
}
```

- **`read_log`:** Fully implemented in Phase 1.4, returning the masked log content enclosed in a protective CDATA XML block.
- **`write_file`:** Fully implemented in Phase 1.5, returning `path`, `resolved_path`, `bytes_written`, and `status: "success"` after evaluating disk space, file system quotas, and parent symlink and junction point integrity.
