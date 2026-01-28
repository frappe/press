import frappe


def ignore_ips() -> str:
	"""
	Returns a space-separated string of IPs to be ignored by fail2ban.
	"""
	return " ".join(frappe.get_all("Monitor Server", pluck="ip"))
