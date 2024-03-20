from frappe.exceptions import ValidationError


class CentralServerNotSet(ValidationError):
	pass


class FrappeioServerNotSet(ValidationError):
	pass


class CannotChangePlan(ValidationError):
	pass


class OngoingAgentJob(ValidationError):
	pass


class MissingAppsInBench(ValidationError):
	pass
