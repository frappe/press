"""Add domains key in press's site configuration (No agent job)."""
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt


from itertools import groupby

import frappe


def execute():
	domain_site_list = frappe.db.sql(
		"""
		SELECT site_domain.name, site.name
		FROM `tabSite Domain` site_domain
		JOIN tabSite site
		ON site_domain.site = site.name
		WHERE
			site_domain.name != site_domain.site and
			site_domain.status = "Active" and
			site.status != "Archived"
		ORDER BY
			site.name
		"""
	)
	domain_site_list = groupby(domain_site_list, lambda x: x[1])
	for site, domains_tuple in domain_site_list:
		domains = [t[0] for t in list(domains_tuple)]
		site = frappe.get_cached_doc("Site", site)
		site._update_configuration({"domains": domains})
