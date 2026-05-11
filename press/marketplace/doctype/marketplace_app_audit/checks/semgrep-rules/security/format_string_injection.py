from frappe import _


def bad_examples():
	try:
		some_method()
	except Exception as e:
		# ruleid: frappe-format-string-injection
		_("Failed to get method {0} with {1}").format(cmd, e)

	try:
		some_method()
	except Exception as e:
		# ruleid: frappe-format-string-injection
		_("Error: {}").format(e)


def good_examples():
	try:
		some_method()
	except Exception as e:
		# ok: frappe-format-string-injection
		_("Failed to get method {0} with {1}").format(cmd, str(e))

	try:
		some_method()
	except Exception as e:
		# ok: frappe-format-string-injection
		_("Error: {}").format(str(e))

	# ok: frappe-format-string-injection
	_("Hello {0}").format(user_name)

	try:
		some_method()
	except Exception as e:
		# ok: frappe-format-string-injection
		_("Error: {}").format(cstr(e))
