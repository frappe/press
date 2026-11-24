import frappe
from frappe.utils.password import get_decrypted_password, set_encrypted_password


def execute():
	for cluster in frappe.get_all("Cluster", pluck="name"):
		if get_decrypted_password("Cluster", cluster, "mariadb_monitor_password", raise_exception=False):
			continue
		password = frappe.generate_hash(length=32)
		set_encrypted_password("Cluster", cluster, password, "mariadb_monitor_password")
