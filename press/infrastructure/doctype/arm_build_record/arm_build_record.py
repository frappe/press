# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import typing

import frappe
from frappe.model.document import Document

from press.agent import Agent
from press.press.doctype.deploy_candidate_build.deploy_candidate_build import Status

if typing.TYPE_CHECKING:
	from press.press.doctype.agent_job.agent_job import AgentJob


class ARMBuildRecord(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.infrastructure.doctype.virtual_machine_arm_image.virtual_machine_arm_image import (
			VirtualMachineARMImage,
		)

		arm_images: DF.Table[VirtualMachineARMImage]
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

	def _pull_images(self, image_tags: list[str]) -> AgentJob:
		return Agent(self.virtual_machine).pull_docker_images(
			image_tags, reference_doctype=self.doctype, reference_name=self.name
		)

	@frappe.whitelist()
	def pull_images(self) -> None:
		builds = [image.build for image in self.arm_images if image.status == Status.SUCCESS.value]
		image_tags = frappe.db.get_all(
			"Deploy Candidate Build", {"name": ("in", builds)}, pluck="docker_image"
		)

		self._pull_images(image_tags)
