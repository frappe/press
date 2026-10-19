# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import re

REDACTED = "********"
SECRET_NAME = r"[\w-]*(?:password|passwd|secret|token)[\w-]*|pwd|(?:api|access|private|encryption)[_-]?key"
# `name=value`, `name: value`, `"name": "value"`; MySQL's "(using password: YES)" is kept
SECRET_ASSIGNMENT_PATTERN = re.compile(
	rf"(?i)\b({SECRET_NAME})(['\"]?\s*[:=]\s*)(?!(?:YES|NO)\b)('[^']*'|\"[^\"]*\"|[^\s,;)\]}}]+)"
)
DOCKER_LOGIN_PASSWORD_PATTERN = re.compile(r"(\bdocker\s+login\b[^\n]*?\s-p\s+)(\S+)")
# `--admin-password value`; `--password-stdin` takes no value
PASSWORD_FLAG_PATTERN = re.compile(
	r"(--(?![\w-]*-stdin\b)[\w-]*(?:password|passwd|secret|token)[\w-]*\s+)(?!-)(\S+)"
)
# The agent passes MySQL/MariaDB passwords attached to the flag: `-p<password>`
MYSQL_PASSWORD_PATTERN = re.compile(
	r"(\b(?:mysql|mariadb)[\w-]*\b[^\n]*?\s-p)(?=[^\s-])('[^']*'|\"[^\"]*\"|\S+)"
)


def redact_secrets(text):
	"""Mask password, token and secret values in job output and tracebacks shown to users"""
	if isinstance(text, list | tuple):
		# A list command's flag and value are separate items, so mask the joined command
		joined = " ".join(str(part) for part in text)
		redacted = redact_secrets(joined)
		return text if redacted == joined else redacted
	if not isinstance(text, str) or not text:
		return text

	for pattern in (DOCKER_LOGIN_PASSWORD_PATTERN, PASSWORD_FLAG_PATTERN, MYSQL_PASSWORD_PATTERN):
		text = pattern.sub(rf"\g<1>{REDACTED}", text)
	return SECRET_ASSIGNMENT_PATTERN.sub(_mask_secret_value, text)


def _mask_secret_value(match: re.Match) -> str:
	name, separator, value = match.groups()
	quote = value[0] if len(value) > 1 and value[0] in "'\"" else ""
	return f"{name}{separator}{quote}{REDACTED}{quote}"
