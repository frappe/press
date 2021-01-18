# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and Contributors
# See license.txt
from __future__ import unicode_literals
from datetime import datetime

import frappe
import unittest


def create_test_remote_file(
	site: str, creation: datetime,
):
	"""Create test remote file doc for required timestamp."""
	return frappe.get_doc(
		{"doctype": "Remote File", "status": "Available", "site": site, "creation": creation}
	).insert(ignore_if_duplicate=True)


class TestRemoteFile(unittest.TestCase):
	pass
