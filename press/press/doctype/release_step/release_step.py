# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt
import typing
from functools import cached_property
from typing import Any

import frappe

from press.press.doctype.bench_update.bench_update import get_bench_update
from press.workflow_engine.doctype.press_workflow.decorators import flow, task
from press.workflow_engine.doctype.press_workflow.workflow_builder import WorkflowBuilder

if typing.TYPE_CHECKING:
	from press.press.doctype.bench_update.bench_update import BenchUpdate
	from press.press.doctype.release_group.release_group import ReleaseGroup


class ReleaseStep(WorkflowBuilder):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.press.doctype.release_step_item.release_step_item import ReleaseStepItem

		release_group: DF.Link | None
		release_step_items: DF.Table[ReleaseStepItem]
		team: DF.Link

	@cached_property
	def release_group_doc(self) -> "ReleaseGroup":
		return frappe.get_doc("Release Group", self.release_group)

	@task
	def validate_app_hashes(self, apps: list[dict[str, str]]):
		"""Validate App Hashes"""
		from press.api.bench import validate_app_hashes

		validate_app_hashes(apps)

	@task
	def validate_server_storages(self):
		"""Validate server storage for all servers in the release group."""
		self.release_group_doc.check_app_server_storage()

	@task
	def validate_auto_scales_on_servers(self):
		"""Validate no server in release group is autoscaled."""
		self.release_group_doc.check_auto_scales()

	@flow
	def create_release(
		self,
		name: str,
		apps: list[dict[str, str]],
		sites: list[dict[str, Any]],
		run_will_fail_checks: bool = False,
	) -> None:
		"""Create a release for the release group."""
		self.validate_app_hashes(apps)
		self.validate_server_storages()
		self.validate_auto_scales_on_servers()

		bench_update: BenchUpdate = get_bench_update(name, apps, sites, is_inplace_update=False)
		bench_update.deploy(
			run_will_fail_check=run_will_fail_checks,
			validate_pre_candidate_checks=False,
		)
