# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and Contributors
# See license.txt


import unittest
from datetime import datetime

import frappe


def create_test_remote_file(
	site: str, creation: datetime = datetime.now(), file_path: str = None
):
	"""Create test remote file doc for required timestamp."""
	return frappe.get_doc(
		{
			"doctype": "Remote File",
			"status": "Available",
			"site": site,
			"creation": creation,
			"file_path": file_path,
		}
	).insert(ignore_if_duplicate=True)


class TestRemoteFile(unittest.TestCase):
	pass
