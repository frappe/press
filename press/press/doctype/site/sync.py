# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt

from press.utils import get_random_names


def sync_setup_wizard_status():
	sites = get_random_names(
		"Site",
		{
			"status": "Active",
			"setup_wizard_complete": False,
			"is_standby": False,
			"domain": ("in", ("erpnext.com", "frappe.cloud", "frappehr.com", "frappedesk.com")),
		},
		limit=20,
	)

	for site_name in sites:
		site = frappe.get_doc("Site", site_name)
		try:
			site.is_setup_wizard_complete()
			frappe.db.commit()
		except Exception:
			frappe.db.rollback()
