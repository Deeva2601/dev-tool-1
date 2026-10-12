"""Replace likely secrets with a fixed placeholder. The rest of the file stays."""

import re

REDACTED = "[REDACTED]"

_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----[\s\S]*?-----END (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----"),
    re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),
    re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
    re.compile(
        r"(?i)(\b(?:api[_-]?key|secret|token|password|passwd|access[_-]?key|private[_-]?key)\b\s*[=:]\s*)(['\"])[^'\"\n]{8,}\2"
    ),
    re.compile(r"(?i)(Authorization:\s*Bearer\s+)[A-Za-z0-9._\-]{8,}"),
)


def redact(text: str) -> str:
    cleaned = text
    for pattern in _PATTERNS:
        if pattern.groups:
            cleaned = pattern.sub(lambda match: f"{match.group(1)}{REDACTED}", cleaned)
        else:
            cleaned = pattern.sub(REDACTED, cleaned)
    return cleaned