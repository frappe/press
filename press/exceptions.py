from frappe.exceptions import ValidationError


class CentralServerNotSet(ValidationError):
	pass


class FrappeioServerNotSet(ValidationError):
	pass
