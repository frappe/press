from frappe.exceptions import ValidationError
from requests import HTTPError


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


class InsufficientSpaceOnServer(ValidationError):
	pass


class VolumeResizeLimitError(ValidationError):
	pass


class AAAARecordExists(ValidationError):
	pass


class ConflictingCAARecord(ValidationError):
	pass


class TeamHeaderNotInRequestError(ValidationError):
	pass


class AlertRuleNotEnabled(ValidationError):
	pass


class SiteUnderMaintenance(ValidationError):
	pass


class SiteAlreadyArchived(ValidationError):
	pass


class InactiveDomains(ValidationError):
	pass


class AgentHTTPError(HTTPError):
	def __init__(
		self, *args, request=None, response=None, status_code=555
	):  # custom status_code exception to suppress err logs
		self.http_status_code = status_code
		super().__init__(*args, request=request, response=response)
