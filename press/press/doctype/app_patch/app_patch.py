# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt

import json
import typing
from typing import Optional, TypedDict

import frappe
import requests
from frappe.model.document import Document
from press.agent import Agent
from press.api.client import dashboard_whitelist

PatchConfig = TypedDict(
	"PatchConfig",
	{
		"patch": Optional[str],
		"filename": str,
		"patch_url": str,
		"build_assets": bool,
		"patch_bench": Optional[str],
		"patch_all_benches": bool,
	},
)

AgentPatchConfig = TypedDict(
	"AgentPatchConfig",
	{
		"patch": str,
		"filename": str,
		"build_assets": bool,
		"revert": bool,
	},
)

if typing.TYPE_CHECKING:
	from press.press.doctype.agent_job.agent_job import AgentJob


class AppPatch(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		app: DF.Link
		app_release: DF.Link
		bench: DF.Link
		build_assets: DF.Check
		filename: DF.Data
		group: DF.Link
		name: DF.Int | None
		patch: DF.Code
		status: DF.Literal["Not Applied", "In Process", "Failed", "Applied"]
		url: DF.Data | None
	# end: auto-generated types

	dashboard_fields = [
		"name",
		"app",
		"app_release",
		"patch",
		"filename",
		"bench",
		"group",
		"build_assets",
		"url",
		"status",
	]

	def validate(self):
		self.validate_bench()

	def validate_bench(self):
		if frappe.get_value("Bench", self.bench, "status") == "Active":
			return
		frappe.throw(f"Bench {self.bench} is not Active, patch cannot be applied")

	def before_insert(self):
		patches = frappe.get_all(
			"App Patch",
			fields=["name", "filename"],
			filters={"bench": self.bench, "patch": self.patch},
		)
		if not len(patches):
			return

		filename = patches[0].get("filename")
		frappe.throw(f"Patch already exists for {self.bench} by the filename {filename}")

	def after_insert(self):
		self.apply_patch()

	@dashboard_whitelist()
	def delete(self):
		super().delete()

	@dashboard_whitelist()
	def apply_patch(self):
		self.patch_app(revert=False)

	@dashboard_whitelist()
	def revert_patch(self):
		self.patch_app(revert=True)

	@frappe.whitelist()
	def delete_patch(self):
		if self.status != "Not Applied":
			frappe.throw(
				f"Cannot delete patch if status is not 'Not Applied'. Current status is '{self.status}'"
			)

		self.delete()

	def patch_app(self, revert: bool):
		server = frappe.db.get_value("Bench", self.bench, "server")
		data = dict(
			patch=self.patch,
			filename=self.filename,
			build_assets=self.build_assets,
			revert=revert,
		)
		Agent(server).patch_app(self, data)
		self.status = "In Process"
		self.save()

	@staticmethod
	def process_patch_app(agent_job: "AgentJob"):
		request_data = json.loads(agent_job.request_data)
		app_patch = frappe.get_last_doc(
			"App Patch",
			{
				"bench": agent_job.bench,
				"patch": request_data.get("patch"),
			},
			for_update=True,
		)

		revert = request_data.get("revert")
		if agent_job.status == "Failure" and revert:
			app_patch.status = "Applied"
		elif agent_job.status == "Failure" and not revert:
			app_patch.status = "Failed"
		elif agent_job.status == "Success" and revert:
			app_patch.status = "Not Applied"
		elif agent_job.status == "Success" and not revert:
			app_patch.status = "Applied"
		else:
			app_patch.status = "In Process"

		app_patch.save()

	@frappe.whitelist()
	def revert_all_patches(self):
		# TODO: Agent job: git reset RELEASE_COMMIT --hard
		pass


def create_app_patch(
	release_group: str, app: str, patch_config: PatchConfig
) -> list[str]:
	patch = get_patch(patch_config)
	benches = get_benches(release_group, patch_config)
	patches = []

	for bench in benches:
		doc_dict = dict(
			doctype="App Patch",
			patch=patch,
			bench=bench,
			group=release_group,
			app=app,
			app_release=get_app_release(bench, app),
			url=patch_config.get("patch_url"),
			filename=patch_config.get("filename"),
			build_assets=patch_config.get("build_assets"),
		)

		app_patch: AppPatch = frappe.get_doc(doc_dict)
		app_patch.insert()
		patches.append(app_patch.name)

	return patches


def get_patch(patch_config: PatchConfig) -> str:
	if patch := patch_config.get("patch"):
		return patch

	patch_url = patch_config.get("patch_url")
	return requests.get(patch_url).text


def get_benches(release_group: str, patch_config: PatchConfig) -> list[str]:
	if not patch_config.get("patch_all_benches"):
		return [patch_config["patch_bench"]]

	return frappe.get_all(
		"Bench",
		filters={"status": "Active", "group": release_group},
		pluck="name",
	)


def get_app_release(bench: str, app: str) -> str:
	return frappe.get_all(
		"Bench App",
		fields=["release"],
		filters={"parent": bench, "app": app},
		pluck="release",
	)[0]
