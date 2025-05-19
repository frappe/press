# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe.model.document import Document

from press.press.doctype.deploy_candidate_build.deploy_candidate_build import Status


class ARMBuild(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.infrastructure.doctype.virtual_machine_arm_image.virtual_machine_arm_image import (
			VirtualMachineARMImage,
		)

		arm_images: DF.Table[VirtualMachineARMImage]
		name: DF.Int | None
		virtual_machine: DF.Link
	# end: auto-generated types

	@frappe.whitelist()
	def sync_status(self):
		for arm_image in self.arm_images:
			if arm_image.status in Status.terminal():
				continue

			current_status = frappe.get_value("Deploy Candidate Build", arm_image.build, "status")
			if arm_image.status != current_status:
				arm_image.status = current_status
				arm_image.save()

	@frappe.whitelist()
	def pull_images(self):
		for arm_image in self.arm_images:
			if arm_image.status != Status.SUCCESS.value:
				continue

			# Pull here in queue
