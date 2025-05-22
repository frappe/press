# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import json
import typing

import frappe
from frappe.model.document import Document

from press.agent import Agent
from press.press.doctype.deploy_candidate_build.deploy_candidate_build import Status

if typing.TYPE_CHECKING:
	from press.press.doctype.agent_job.agent_job import AgentJob
	from press.press.doctype.bench.bench import Bench


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

	def _pull_images(self, image_tags: list[str]) -> AgentJob:
		return Agent(self.virtual_machine).pull_docker_images(
			image_tags, reference_doctype=self.doctype, reference_name=self.name
		)

	def _update_image_tags_on_benches(self):
		"""Maybe enqueue this?"""
		for image in self.arm_images:
			new_docker_image = frappe.get_value("Deploy Candidate Build", image.build, "docker_image")
			bench: Bench = frappe.get_doc("Bench", image.bench)
			bench.docker_image = new_docker_image
			bench_config = json.loads(bench.bench_config)
			bench_config["docker_image"] = new_docker_image
			bench.bench_config = json.dumps(bench_config, indent=4)
			bench.save()

	def _check_images_pulled(self) -> bool:
		try:
			agent_job: AgentJob = frappe.get_last_doc(
				"Agent Job", {"reference_doctype": self.doctype, "reference_name": self.name}
			)
		except frappe.DoesNotExistError:
			return False
		return agent_job.status == "Success"

	@frappe.whitelist()
	def pull_images(self):
		"""Pull images on app server using image tags"""
		builds = [image.build for image in self.arm_images if image.status == Status.SUCCESS.value]
		image_tags = frappe.db.get_all(
			"Deploy Candidate Build", {"name": ("in", builds)}, pluck="docker_image"
		)
		self._pull_images(image_tags)

	@frappe.whitelist()
	def update_image_tags_on_benches(self):
		"""
		This step replaces the image tags on the app server itself.
		If the image does not exist when this is called and bench tries to start
		it will fail.
		"""
		if not self._check_images_pulled():
			frappe.throw(
				"ARM images have not been successfully pulled on the server",
				frappe.ValidationError,
			)
		self._update_image_tags_on_benches()

	@frappe.whitelist()
	def sync_status(self):
		for arm_image in self.arm_images:
			if arm_image.status in Status.terminal():
				continue

			current_status = frappe.get_value("Deploy Candidate Build", arm_image.build, "status")
			if arm_image.status != current_status:
				arm_image.status = current_status
				arm_image.save()
