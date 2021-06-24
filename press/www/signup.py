# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# Proprietary License. See license.txt

from __future__ import unicode_literals
from frappe.geo.country_info import get_country_info


def get_context():
	return {"country_info": get_country_info()}
