# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
import frappe


def number_k_format(number: int):
	"""Returns a '101.6k' like string representation"""
	if number < 1000:
		return str(number)
	else:
		value = frappe.utils.rounded(number / 1000, precision=1)

		# To handle cases like 8.0, 9.0 etc.
		if value == (number // 1000):
			value = int(value)
		# To handle cases like 8999 -> 9k and not 9.0k
		elif (value - 1) == (number // 1000):
			value = int(value)

		return f"{value}k"
