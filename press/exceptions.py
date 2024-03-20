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
	def __init__(self, site: str = "", apps: set = [], bench: str = ""):
		super().__init__(
			f"Bench {bench} doesn't have some of the apps installed on {site}{': ' if apps else ''}{', '.join(apps)}",
		)
