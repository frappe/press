import ipaddress

import frappe
from frappe.utils import cstr

PRIVATE_NETWORKS = ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")


def ignore_ips() -> str:
	"""
	Returns a space-separated string of IPs and networks that fail2ban must never ban.
	"""
	return " ".join([*PRIVATE_NETWORKS, *proxy_server_ips(), *bastion_server_ips(), *press_settings_ips()])


def proxy_server_ips() -> list[str]:
	return frappe.get_all("Proxy Server", {"status": ("!=", "Archived"), "ip": ("is", "set")}, pluck="ip")


def bastion_server_ips() -> list[str]:
	return frappe.get_all("Bastion Server", {"status": ("!=", "Archived"), "ip": ("is", "set")}, pluck="ip")


def press_settings_ips() -> list[str]:
	return parse_ips(frappe.db.get_single_value("Press Settings", "fail2ban_ignore_ips"))


def parse_ips(value) -> list[str]:
	return cstr(value).split()


def validate_ips(value):
	for ip in parse_ips(value):
		try:
			ipaddress.ip_network(ip, strict=False)
		except ValueError:
			frappe.throw(
				f"{ip} in Fail2Ban Ignore IPs is not an IP address or network. "
				"Enter one IP address or CIDR network, like 203.0.113.7 or 203.0.113.0/24, per line."
			)
