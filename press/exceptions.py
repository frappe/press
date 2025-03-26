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


class DNSValidationError(ValidationError):
	pass


class AAAARecordExists(DNSValidationError):
	pass


class ConflictingCAARecord(DNSValidationError):
	pass


class ConflictingDNSRecord(DNSValidationError):
	pass


class MultipleARecords(DNSValidationError):
	pass


class MultipleCNAMERecords(DNSValidationError):
	pass


class TLSRetryLimitExceeded(ValidationError):
	pass
