import functools
from typing import Any

import frappe

REDACTED = "[REDACTED]"
MAX_DEPTH = 20


def _clamp(value: Any, default: int, lo: int, hi: int) -> int:
	try:
		return max(lo, min(int(value or default), hi))
	except Exception:
		return default


def system_manager_only(fn):
	@functools.wraps(fn)
	def wrapper(*args, **kwargs):
		frappe.only_for("System Manager")
		return fn(*args, **kwargs)

	return wrapper
