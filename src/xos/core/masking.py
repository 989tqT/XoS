"""Secure log masking engine for PII removal and Second-Order Prompt Injection defense."""

from __future__ import annotations

import re

MAX_LINE_LENGTH = 4096

# bounded regex pattern to prevent ReDoS (zero-dependency approach with rigorous pattern hardening)
MULTILINE_MASK_PATTERNS = [
    # ssh private key
    (
        re.compile(
            r"-----BEGIN [A-Z]{3,15} PRIVATE KEY-----[^\n]{0,100}\n[\s\S]{10,2000}?"
            r"-----END [A-Z]{3,15} PRIVATE KEY-----"
        ),
        "[MASKED_SSH_KEY]",
    ),
]

MASK_PATTERNS = [
    # aws access key
    (re.compile(r"\b(AKIA|ASCA|ASIA)[0-9A-Z]{16}\b"), "[MASKED_AWS_KEY]"),
    # github token
    (re.compile(r"\bgh[ps]_[a-zA-Z0-9]{36}\b"), "[MASKED_GITHUB_TOKEN]"),
    # credentials key-value pair
    (
        re.compile(
            r"(?i)\b(password|secret|passwd|token|api_key|credential)\s*[:=]\s*['\"]?[a-zA-Z0-9_\-\.\@\#\$\%\^\&\*\(\)]{1,64}['\"]?"
        ),
        r"\1: [MASKED_CREDENTIAL]",
    ),
    # email address (strictly bounded to avoid ReDoS)
    (
        re.compile(r"\b[a-zA-Z0-9._%+-]{1,64}@[a-zA-Z0-9.-]{1,63}\.[a-zA-Z]{2,10}\b"),
        "[MASKED_EMAIL]",
    ),
    # ipv4 address
    (re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"), "[MASKED_IP]"),
]

DIRECTIVE_PATTERNS = [
    (
        re.compile(r"(?i)\bignore\s+(?:all\s+)?previous\s+(?:instructions|directives)\b"),
        "[SUSPICIOUS_DIRECTIVE_REMOVED]",
    ),
    (re.compile(r"(?i)\bsystem\s+override\b"), "[SUSPICIOUS_DIRECTIVE_REMOVED]"),
    (re.compile(r"(?i)\bforget\s+(?:all\s+)?rules\b"), "[SUSPICIOUS_DIRECTIVE_REMOVED]"),
    (re.compile(r"(?i)\byou\s+are\s+now\b"), "[SUSPICIOUS_DIRECTIVE_REMOVED]"),
]


def escape_cdata(text: str) -> str:
    """Escape CDATA sequence ']]>' to prevent prompt injection escaping the CDATA container."""
    return text.replace("]]>", "]]&gt;<![CDATA[")


def mask_line(line: str) -> str:
    """Apply PII, secret, and prompt injection directive masking to a single line of log.

    Enforces strict line length limits before scanning to mitigate ReDoS.
    """
    # 1. defense-in-depth: truncate long line to prevent CPU/memory exhaustion and ReDoS
    if len(line) > MAX_LINE_LENGTH:
        line = line[:MAX_LINE_LENGTH] + "\n[TRUNCATED_BY_SECURITY_POLICY]"

    # 2. mask PII & secret
    for pattern, replacement in MASK_PATTERNS:
        line = pattern.sub(replacement, line)

    # 3. mask suspicious directive
    for pattern, replacement in DIRECTIVE_PATTERNS:
        line = pattern.sub(replacement, line)

    return line


def secure_envelope_cdata(content: str) -> str:
    """Apply masking, escape CDATA boundaries, and wrap in XML CDATA tags."""
    # 1. mask multiline pattern (like ssh private key) globally first
    for pattern, replacement in MULTILINE_MASK_PATTERNS:
        content = pattern.sub(replacement, content)

    # 2. process line-by-line to prevent ReDoS on massive assembled block
    lines = content.splitlines(keepends=True)
    masked_lines = [mask_line(line) for line in lines]
    masked_content = "".join(masked_lines)

    escaped = escape_cdata(masked_content)
    return f"<log_content><![CDATA[{escaped}]]></log_content>"
