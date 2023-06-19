# Copyright (c) 2022, Frappe and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.virtual_machine_image.virtual_machine_image import (
	VirtualMachineImage,
)


def create_test_virtual_machine_image(
	ip: str = frappe.mock("ipv4"),
) -> VirtualMachineImage:
	"""Create test Virtual Machine Image doc"""
	from press.press.doctype.virtual_machine.test_virtual_machine import (
		create_test_virtual_machine,
	)

	return frappe.get_doc(
		{
			"doctype": "Virtual Machine Image",
			"virtual_machine": create_test_virtual_machine().name,
			"series": "m",
			"status": "Active",
		}
	).insert(ignore_if_duplicate=True)


class TestVirtualMachineImage(FrappeTestCase):
	pass
