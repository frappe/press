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
