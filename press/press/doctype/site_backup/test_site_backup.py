# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and Contributors
# See license.txt


import unittest
from datetime import datetime

import frappe
from press.press.doctype.remote_file.test_remote_file import create_test_remote_file


def create_test_site_backup(
	site: str,
	creation: datetime = datetime.now(),
	files_availability: str = "Available",
	offsite: bool = True,
	status: str = "Success",
):
	"""
	Create test site backup doc for required timestamp.

	Makes offsite backups by default along with remote files.
	"""
	params_dict = {
		"doctype": "Site Backup",
		"status": status,
		"site": site,
		"creation": creation,
		"files_availability": files_availability,
		"offsite": offsite,
	}
	if offsite:
		params_dict["remote_public_file"] = create_test_remote_file(site, creation).name
		params_dict["remote_private_file"] = create_test_remote_file(site, creation).name
		params_dict["remote_database_file"] = create_test_remote_file(site, creation).name
	return frappe.get_doc(params_dict).insert(ignore_if_duplicate=True)


class TestSiteBackup(unittest.TestCase):
	pass
