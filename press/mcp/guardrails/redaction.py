import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Any

REDACTED = "[REDACTED]"
MAX_DEPTH = 20


SENSITIVE_KEYS = {
	# auth
	"password",
	"passwd",
	"pwd",
	"secret",
	"token",
	"access_token",
	"refresh_token",
	"auth_token",
	"authorization",
	"bearer_token",
	# api
	"api_key",
	"apikey",
	"api_secret",
	# frappe
	"sid",
	"csrf_token",
	# db
	"db_password",
	"root_password",
	"admin_password",
	"mariadb_root_password",
	# press / infra
	"ssh_private_key",
	"private_key",
	"registry_password",
	"registry_token",
	"docker_password",
	"webhook_secret",
	# cloud
	"aws_secret_access_key",
	"secret_access_key",
	"secret_key",
	# oauth
	"client_secret",
	"jwt_secret",
	# email
	"smtp_password",
}


SENSITIVE_KEY_PARTS = {
	"password",
	"passwd",
	"pwd",
	"secret",
	"token",
	"api_key",
	"apikey",
	"api_secret",
	"public_key",
	"private_key",
	"access_key",
	"csrf",
	"sid",
}


@dataclass(frozen=True)
class RedactionPattern:
	pattern: re.Pattern
	keep_prefix: bool


PATTERNS = [
	# Authorization: Bearer xxx
	RedactionPattern(
		re.compile(r"(Authorization:\s*\S+\s+)\S+", re.IGNORECASE),
		keep_prefix=True,
	),
	# Bearer xxx
	RedactionPattern(
		re.compile(r"(bearer\s+)[A-Za-z0-9\-._~+/]+=*", re.IGNORECASE),
		keep_prefix=True,
	),
	# URL params
	RedactionPattern(
		re.compile(
			r"([?&](?:token|api_?key|secret|password|passwd|pwd|sid|csrf_token)=)[^&\s\"']+",
			re.IGNORECASE,
		),
		keep_prefix=True,
	),
	# JSON / config values
	RedactionPattern(
		re.compile(
			r'("?(?:password|passwd|pwd|secret|token|api_?key|sid|csrf_token|db_password|root_password|admin_password|secret_access_key|private_key)"?\s*[":=]\s*)["\']?[^"\'}\s,\n]+',
			re.IGNORECASE,
		),
		keep_prefix=True,
	),
	# DB URLs
	RedactionPattern(
		re.compile(
			r"((?:mysql|postgresql|postgres|mariadb|mongodb|redis)://[^:@\s]+:)[^@\s]+",
			re.IGNORECASE,
		),
		keep_prefix=True,
	),
	# redis://:password@
	RedactionPattern(
		re.compile(
			r"((?:redis|rediss)://:)[^@]+",
			re.IGNORECASE,
		),
		keep_prefix=True,
	),
	# Cookie header
	RedactionPattern(
		re.compile(r"(Cookie:\s*).+", re.IGNORECASE),
		keep_prefix=True,
	),
	# sid cookie
	RedactionPattern(
		re.compile(r"(sid=)[^;\"'\s]+", re.IGNORECASE),
		keep_prefix=True,
	),
	# JWT
	RedactionPattern(
		re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9._-]+\.[A-Za-z0-9._-]+\b"),
		keep_prefix=False,
	),
	# SSH/private keys
	RedactionPattern(
		re.compile(
			r"-----BEGIN [A-Z ]+ PRIVATE KEY-----.*?-----END [A-Z ]+ PRIVATE KEY-----",
			re.DOTALL,
		),
		keep_prefix=False,
	),
]


def redact(value: Any, depth: int = 0) -> Any:
	"""
	Recursively redact secrets from logs, configs and tool output.

	This function is intentionally strict and has no bypass/options.
	Use this before sending any tool output or context to an LLM or to a human.
	"""

	if depth > MAX_DEPTH:
		return REDACTED

	if isinstance(value, str):
		return _redact_string(value)

	if isinstance(value, bytes):
		return REDACTED

	if isinstance(value, dict):
		return {
			key: REDACTED if _is_sensitive_key(key) and item is not None else redact(item, depth=depth + 1)
			for key, item in value.items()
		}

	if isinstance(value, list):
		return [redact(item, depth=depth + 1) for item in value]

	if isinstance(value, tuple):
		return tuple(redact(item, depth=depth + 1) for item in value)

	if isinstance(value, set):
		return {redact(item, depth=depth + 1) for item in value}

	return value


def _normalize_key(key: str) -> str:
	return key.strip().lower().replace("-", "_").replace(" ", "_").replace(".", "_")


def _is_sensitive_key(key: Any) -> bool:
	if not isinstance(key, str):
		return False

	normalized = _normalize_key(key)

	if normalized in SENSITIVE_KEYS:
		return True

	return any(part in normalized for part in SENSITIVE_KEY_PARTS)


TOKEN_LIKE_PATTERN = re.compile(r"^[A-Za-z0-9_\-+=./@$!%*#?&]+$")


def _looks_like_secret(value: str) -> bool:
	value = value.strip()

	if len(value) < 16:
		return False

	if " " in value:
		return False

	if not TOKEN_LIKE_PATTERN.match(value):
		return False

	# avoid normal paths / URLs
	if value.count("/") > 3:
		return False

	# avoid boring repeated strings
	if len(set(value)) < 6:
		return False

	# count shannon entropy
	counter = Counter(value)
	length = len(value)

	entropy = -sum((count / length) * math.log2(count / length) for count in counter.values())
	return entropy >= 4.8


def _redact_string(value: str) -> str:
	for item in PATTERNS:

		def replace(match):
			if item.keep_prefix:
				return f"{match.group(1)}{REDACTED}"

			return REDACTED

		value = item.pattern.sub(replace, value)

	if _looks_like_secret(value):
		return REDACTED

	return value
