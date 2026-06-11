from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

REDACTION_VERSION = "support-agent-redaction-v1"

EMAIL_PATTERN = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
PHONE_PATTERN = re.compile(r"(?<!\w)(?:\+?\d[\d\s().-]{7,}\d)(?!\w)")
IPV4_PATTERN = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
SECRET_PATTERN = re.compile(
	r"(?i)\b(api[_-]?key|access[_-]?key|secret|token|password|authorization|cookie)\b\s*[:=]\s*([^\s,;]+)"
)
AUTH_HEADER_PATTERN = re.compile(r"(?i)\bauthorization\s*:\s*bearer\s+[^\s,;]+")
BEARER_PATTERN = re.compile(r"(?i)\bbearer\s+[a-z0-9._~+/=-]+")


def redact(value: Any) -> Any:
	if isinstance(value, str):
		return redact_text(value)

	if isinstance(value, Mapping):
		return {key: redact(_redacted_secret_value(key, item)) for key, item in value.items()}

	if isinstance(value, Sequence) and not isinstance(value, bytes | bytearray):
		return [redact(item) for item in value]

	return value


def redact_text(value: str) -> str:
	value = AUTH_HEADER_PATTERN.sub("Authorization: Bearer [REDACTED]", value)
	value = BEARER_PATTERN.sub("Bearer [REDACTED]", value)
	value = SECRET_PATTERN.sub(lambda match: f"{match.group(1)}=[REDACTED]", value)
	value = EMAIL_PATTERN.sub("[REDACTED_EMAIL]", value)
	value = PHONE_PATTERN.sub("[REDACTED_PHONE]", value)
	return IPV4_PATTERN.sub("[REDACTED_IP]", value)


def _redacted_secret_value(key: Any, value: Any) -> Any:
	if isinstance(key, str) and any(
		fragment in key.lower() for fragment in ("password", "secret", "token", "api_key", "apikey", "cookie")
	):
		return "[REDACTED]"
	return value
