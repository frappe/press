import functools

import frappe

SETTINGS_DOCTYPE = "Press Settings"


def enabled(key: str, default_value=None, raise_error: bool = False):
	"""
	Decorator to check if a feature is enabled in Press Settings.

	Example:
	```python
	@settings.enabled("some_feature_key")
	def some_function():
	    pass
	```
	"""

	def wrapped(func):
		@functools.wraps(func)
		def inner(*args, **kwargs):
			if frappe.db.get_single_value(SETTINGS_DOCTYPE, key, cache=True):
				return func(*args, **kwargs)
			if raise_error:
				frappe.throw("This feature is disabled", frappe.ValidationError)
			return default_value

		return inner

	return wrapped
