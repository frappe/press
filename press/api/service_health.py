import frappe


@frappe.whitelist(allow_guest=True)
def service_health():
	"""
	Check if more than 50% of records for each service in the past 5 minutes are failing.
	Returns a dictionary with service names and a boolean, True -> poor health.
	"""
	services_to_check = ["Deploy Candidate Build", "Site Backup"]
	filters = {"creation": ("between", [frappe.utils.add_to_date(minutes=-5), frappe.utils.now()])}
	health_status = {}

	for service in services_to_check:
		total_count = frappe.db.count(service, filters)

		if total_count == 0:
			health_status[service] = False
			continue

		failing_count = frappe.db.count(service, {**filters, "status": "Failure"})

		failure_rate = (failing_count / total_count) * 100
		health_status[service] = failure_rate > 50

	return health_status
