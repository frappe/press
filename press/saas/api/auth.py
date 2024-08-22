# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

import frappe
from press.saas.api import whitelist_saas_api


@whitelist_saas_api
def generate_access_token():
	from press.saas.doctype.site_access_token.site_access_token import SiteAccessToken

	return SiteAccessToken.generate(frappe.local.site_name)
