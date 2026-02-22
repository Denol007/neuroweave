"""PII Anonymizer — detects and redacts personally identifiable information.

MVP implementation using regex patterns. Catches:
- Email addresses
- IP addresses (v4 and v6)
- Phone numbers (international formats)
- URLs containing usernames or auth tokens
- File paths with usernames (/Users/john/, /home/john/)
- Discord user mentions in text (@username patterns)
- API keys / tokens (common formats)

Future: integrate Llama 3.2 1B PII model for higher recall.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import structlog

logger = structlog.get_logger()


@dataclass
class AnonymizationResult:
    """Result of anonymizing a text."""

    text: str
    redactions: list[dict] = field(default_factory=list)

    @property
    def redaction_count(self) -> int:
        return len(self.redactions)


# --- Compiled regex patterns ---

_EMAIL_RE = re.compile(
    r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
)

_IPV4_RE = re.compile(
    r'\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b'
)

_IPV6_RE = re.compile(
    r'\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b'
    r'|\b(?:[0-9a-fA-F]{1,4}:){1,7}:\b'
    r'|\b::(?:[0-9a-fA-F]{1,4}:){0,5}[0-9a-fA-F]{1,4}\b'
)

_PHONE_RE = re.compile(
    r'(?<!\d)'
    r'(?:\+?\d{1,3}[-.\s]?)?'
    r'(?:\(?\d{2,4}\)?[-.\s]?)'
    r'\d{3,4}[-.\s]?\d{3,4}'
    r'(?!\d)'
)

_URL_WITH_AUTH_RE = re.compile(
    r'[a-zA-Z][a-zA-Z0-9+.-]*://[^:]+:[^@]+@[^\s]+'
)

_FILE_PATH_RE = re.compile(
    r'(?:/(?:Users|home|root)/[A-Za-z0-9._-]+)'
    r'(?:/[A-Za-z0-9._/-]*)?'
)

_API_KEY_RE = re.compile(
    r'\b(?:'
    r'sk-[A-Za-z0-9]{20,}'          # OpenAI / Anthropic style
    r'|ghp_[A-Za-z0-9]{20,}'         # GitHub PAT
    r'|xox[bpsar]-[A-Za-z0-9-]+'    # Slack tokens
    r'|AIza[A-Za-z0-9_-]{35}'       # Google API key
    r'|AKIA[A-Z0-9]{16}'            # AWS access key
    r')\b'
)

_DISCORD_MENTION_RE = re.compile(
    r'@[A-Za-z0-9_]{2,32}(?:#\d{4})?'
)


# --- Pattern registry ---

_PATTERNS: list[tuple[str, re.Pattern, str]] = [
    # URL_AUTH must run before EMAIL to avoid partial matches
    ("URL_AUTH", _URL_WITH_AUTH_RE, "[URL_REDACTED]"),
    ("EMAIL", _EMAIL_RE, "[EMAIL]"),
    ("IPV4", _IPV4_RE, "[IP]"),
    ("IPV6", _IPV6_RE, "[IP]"),
    ("PHONE", _PHONE_RE, "[PHONE]"),
    ("FILE_PATH", _FILE_PATH_RE, "[PATH]"),
    ("API_KEY", _API_KEY_RE, "[API_KEY]"),
    ("DISCORD_MENTION", _DISCORD_MENTION_RE, "[USER]"),
]


def anonymize(text: str) -> AnonymizationResult:
    """Redact PII from text using regex patterns.

    Args:
        text: Raw text potentially containing PII.

    Returns:
        AnonymizationResult with redacted text and list of redactions.
    """
    redactions: list[dict] = []
    result = text

    for pii_type, pattern, replacement in _PATTERNS:
        matches = list(pattern.finditer(result))
        if not matches:
            continue

        # Process matches in reverse order to preserve positions
        for match in reversed(matches):
            original = match.group()

            # Skip very short matches for phone (false positives)
            if pii_type == "PHONE" and len(original.replace(" ", "").replace("-", "")) < 7:
                continue

            # Skip localhost IPs (not PII)
            if pii_type == "IPV4" and original.startswith("127.") or original == "0.0.0.0":
                continue

            redactions.append({
                "type": pii_type,
                "original": original,
                "replacement": replacement,
                "start": match.start(),
                "end": match.end(),
            })
            result = result[:match.start()] + replacement + result[match.end():]

    if redactions:
        logger.debug(
            "pii_redacted",
            count=len(redactions),
            types=[r["type"] for r in redactions],
        )

    return AnonymizationResult(text=result, redactions=redactions)


def anonymize_batch(texts: list[str]) -> list[AnonymizationResult]:
    """Anonymize a batch of texts."""
    return [anonymize(t) for t in texts]
