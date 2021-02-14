# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest


def create_test_cluster(name: str = "default"):
	"""Create test Cluster doc"""
	return frappe.get_doc({"doctype": "Cluster", "name": name}).insert(
		ignore_if_duplicate=True
	)


class TestCluster(unittest.TestCase):
	pass
