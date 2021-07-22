# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe and Contributors
# See license.txt
from __future__ import unicode_literals
from press.press.doctype.root_domain.root_domain import RootDomain

import unittest
from unittest.mock import Mock, patch

import frappe

from press.press.doctype.cluster.test_cluster import create_test_cluster


@patch.object(RootDomain, "after_insert", new=Mock())
def create_test_root_domain(name: str):
	return frappe.get_doc(
		{
			"doctype": "Root Domain",
			"name": name,
			"default_cluster": create_test_cluster().name,
			"aws_access_key_id": "a",
			"aws_secret_access_key": "b",
		}
	).insert(ignore_if_duplicate=True)


class TestRootDomain(unittest.TestCase):
	pass
