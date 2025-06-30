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
	from press.press.doctype.server.server import Server


class ARMBuildRecord(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.infrastructure.doctype.arm_docker_image.arm_docker_image import ARMDockerImage

		arm_images: DF.Table[ARMDockerImage]
		server: DF.Link
		updated_image_tags_on_benches: DF.Check
	# end: auto-generated types

	def _pull_images(self, image_tags: list[str]) -> AgentJob:
		server: Server = frappe.get_doc("Server", self.server)
		server._update_agent_ansible()
		return Agent(self.server).pull_docker_images(
			image_tags, reference_doctype=self.doctype, reference_name=self.name
		)

	def _update_redis_conf(self, bench: Bench) -> None:
		"""Update redis-queue.conf & redis-cache.conf with new arm redisearch.so location"""
		command = """sed -i 's|loadmodule /home/frappe/frappe-bench/redis/redisearch.so|loadmodule /home/frappe/frappe-bench/redis/arm64/redisearch.so|' /home/frappe/frappe-bench/config/redis-cache.conf /home/frappe/frappe-bench/config/redis-queue.conf"""
		bench.docker_execute(command)

	def _update_image_tags_on_benches(self):
		if self.updated_image_tags_on_benches:
			return

		for image in self.arm_images:
			new_docker_image = frappe.get_value("Deploy Candidate Build", image.build, "docker_image")
			bench: Bench = frappe.get_doc("Bench", image.bench)
			bench.build = image.build
			bench.docker_image = new_docker_image
			bench_config = json.loads(bench.bench_config)
			bench_config["docker_image"] = new_docker_image
			bench.bench_config = json.dumps(bench_config, indent=4)
			self._update_redis_conf(bench)
			bench.save()

		# Once the benches are updated with latest images, we can then start migration.
		# And once the migration is completed we then just need to start all benches on the server
		# and new images which have been pulled will be used to restart the docker containers.

		frappe.set_value("Virtual Machine", self.server, "ready_for_conversion", True)
		self.updated_image_tags_on_benches = True
		self.save(ignore_version=True)

	def _check_images_pulled(self) -> bool:
		try:
			agent_job: AgentJob = frappe.get_last_doc(
				"Agent Job", {"reference_doctype": self.doctype, "reference_name": self.name}
			)
		except frappe.DoesNotExistError:
			return False
		return agent_job.status == "Success"

	@frappe.whitelist()
	def remove_build_from_deploy_candidate(self, build: str):
		"""
		Remove arm build field from deploy candidate.
		(when new arm build record is attempted a fresh build will be created).
		"""
		deploy_candidate = frappe.db.get_value("Deploy Candidate Build", build, "deploy_candidate")
		frappe.db.set_value("Deploy Candidate", deploy_candidate, "arm_build", None)
		frappe.db.commit()

	@frappe.whitelist()
	def retry(self):
		server: Server = frappe.get_doc("Server", self.server)
		server.collect_arm_images()
		self.delete(ignore_permissions=True)

	@frappe.whitelist()
	def cancel_all_jobs(self):
		"""Cancel all current running jobs"""
		self.sync_status()

		for arm_image in self.arm_images:
			if arm_image.status == "Running":
				agent_job: "AgentJob" = frappe.get_doc(
					"Agent Job",
					{"reference_doctype": "Deploy Candidate Build", "reference_name": arm_image.build},
				)
				agent_job.cancel_job()

		self.sync_status()

	@frappe.whitelist()
	def pull_images(self):
		"""Pull images on app server using image tags"""
		builds = []
		self.sync_status()

		for image in self.arm_images:
			if image.status != Status.SUCCESS.value:
				frappe.throw("Some builds failed skipping image pull!", frappe.ValidationError)
			builds.append(image.build)

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
				f"ARM images have not been successfully pulled on {self.server}",
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
