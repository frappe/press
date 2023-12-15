# Copyright (c) 2022, Frappe and Contributors
# See license.txt

from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.cluster.cluster import Cluster
from press.press.doctype.cluster.test_cluster import create_test_cluster
from press.press.doctype.virtual_machine_image.virtual_machine_image import (
	VirtualMachineImage,
)


@patch.object(VirtualMachineImage, "client", new=MagicMock())
@patch.object(VirtualMachineImage, "after_insert", new=MagicMock())
def create_test_virtual_machine_image(
	ip: str = None,
	cluster: Cluster = None,
	series: str = "m",
) -> VirtualMachineImage:
	"""Create test Virtual Machine Image doc"""
	if not ip:
		ip = frappe.mock("ipv4")
	if not cluster:
		cluster = create_test_cluster()
	from press.press.doctype.virtual_machine.test_virtual_machine import (
		create_test_virtual_machine,
	)

	vm = create_test_virtual_machine(cluster=cluster, series=series)

	return frappe.get_doc(
		{
			"doctype": "Virtual Machine Image",
			"virtual_machine": vm.name,
			"region": vm.region,
			"status": "Available",
			"image_id": "ami-1234567890",
			"mariadb_root_password": "password",
		}
	).insert(ignore_if_duplicate=True)


class TestVirtualMachineImage(FrappeTestCase):
	pass
