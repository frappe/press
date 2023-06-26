# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe and Contributors
# See license.txt


import frappe
import unittest

from press.press.doctype.ssh_key.test_ssh_key import create_test_ssh_key

from press.press.doctype.cluster.cluster import Cluster

from unittest.mock import MagicMock, patch


@patch.object(Cluster, "after_insert", new=MagicMock())
def create_test_cluster(name: str = "Mumbai", region: str = "ap-south-1") -> Cluster:
	"""Create test Cluster doc"""
	return frappe.get_doc(
		{
			"doctype": "Cluster",
			"name": name,
			"region": region,
			"availability_zone": "ap-south-1a",
			"cloud_provider": "AWS EC2",
			"ssh_key": create_test_ssh_key().name,
			"subnet_cidr_block": "10.3.0.0/16",
		}
	).insert(ignore_if_duplicate=True)


class TestCluster(unittest.TestCase):
	pass
