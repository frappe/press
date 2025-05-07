# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt


"""
- Take cognizance of deploy candidate bench and deploy as well (get_deploy_bench_candidate).
- For all deploy candidate make a deploy candidate build copied all build fields into deploy candidate build (create_deploy_candidate_build).
- Copy all build steps from deploy candidate to deploy candidate build (update_build_step_parent).
- Copy deploy candidate build name to all deploy and bench associated with it (add_deploy_and_bench_to_build).
"""

from __future__ import annotations

import time
import typing

import frappe
from frappe.query_builder import Order

DeployCandidate = frappe.qb.DocType("Deploy Candidate")
DeployCandidateBuild = frappe.qb.DocType("Deploy Candidate Build")
Bench = frappe.qb.DocType("Bench")
Deploy = frappe.qb.DocType("Deploy")
DeployCandidateBuildStep = frappe.qb.DocType("Deploy Candidate Build Step")


class CandidateInfo(typing.TypedDict):
	deploy_candidate: str
	deploy_candidate_group: str
	deploy_candidate_team: str
	deploy_candidate_status: str
	deploy_candidate_docker_image: str
	deploy_candidate_docker_image_repository: str
	deploy_candidate_docker_image_id: str
	deploy_candidate_docker_image_tag: str
	deploy_candidate_build_output: str
	deploy_candidate_build_error: str


def get_deploy_bench_candidate(
	offset: int, limit: str, existing_deploy_candidate_builds: list[str]
) -> list[CandidateInfo]:
	"""Fetch all deploy candidates and their corresponding bench and deploy which don't have a build"""
	deploy_candidates: list[CandidateInfo] = (
		frappe.qb.from_(DeployCandidate)
		.select(
			(DeployCandidate.name).as_("deploy_candidate"),
			(DeployCandidate.group).as_("deploy_candidate_group"),
			(DeployCandidate.team).as_("deploy_candidate_team"),
			(DeployCandidate.status).as_("deploy_candidate_status"),
			(DeployCandidate.docker_image).as_("deploy_candidate_docker_image"),
			(DeployCandidate.docker_image_repository).as_("deploy_candidate_docker_image_repository"),
			(DeployCandidate.docker_image_id).as_("deploy_candidate_docker_image_id"),
			(DeployCandidate.docker_image_tag).as_("deploy_candidate_docker_image_tag"),
			(DeployCandidate.build_error).as_("deploy_candidate_build_error"),
			(DeployCandidate.build_output).as_("deploy_candidate_build_output"),
		)
		.offset(offset)
		.limit(limit)
		.where(
			DeployCandidate.status.notin(["Draft", "Scheduled"])
		)  # We don't want to create a build for scheduled & draft deploy candidates
		.where(DeployCandidate.name.notin(existing_deploy_candidate_builds))
		.orderby(DeployCandidate.modified, order=Order.desc)
		.run(as_dict=True)
	)

	return deploy_candidates


def create_deploy_candidate_build(deploy_candidate: CandidateInfo) -> str:
	"""Create deploy candidate build for each deploy candidate"""
	deploy_candidate_build = frappe.new_doc(
		"Deploy Candidate Build",
		**{
			"deploy_candidate": deploy_candidate["deploy_candidate"],
			"group": deploy_candidate["deploy_candidate_group"],
			"team": deploy_candidate["deploy_candidate_team"],
			"status": deploy_candidate["deploy_candidate_status"],
			"docker_image_id": deploy_candidate["deploy_candidate_docker_image_id"],
			"docker_image_tag": deploy_candidate["deploy_candidate_docker_image_tag"],
			"docker_image_repository": deploy_candidate["deploy_candidate_docker_image_repository"],
			"docker_image": deploy_candidate["deploy_candidate_docker_image"],
			"build_output": deploy_candidate["deploy_candidate_build_output"],
			"build_error": deploy_candidate["deploy_candidate_build_error"],
			"run_build": False,
		},
	).insert(ignore_permissions=True)
	add_build_to_deploy_and_bench(
		deploy_candidate_name=deploy_candidate["deploy_candidate"],
		deploy_candidate_build_name=deploy_candidate_build.name,
	)
	return deploy_candidate_build.name


def update_build_step_parent(deploy_candidate_name: str, deploy_candidate_build_name: str):
	"""Copy build step parent to deploy candidate build"""
	if deploy_candidate_build_name is None:
		raise Exception(f"Migration Failure Deploy Candidate Build: {deploy_candidate_build_name}")

	frappe.db.sql(
		"UPDATE `tabDeploy Candidate Build Step` SET parent=%s, parenttype='Deploy Candidate Build' WHERE parent=%s AND parenttype='Deploy Candidate'",
		(deploy_candidate_build_name, deploy_candidate_name),
	)


def add_build_to_deploy_and_bench(deploy_candidate_name: str, deploy_candidate_build_name: str):
	"""Add build to deploy and bench if they exist"""
	if deploy_candidate_build_name is None or deploy_candidate_name is None:
		raise Exception(f"Migration failed: {deploy_candidate_build_name}:{deploy_candidate_name}")

	frappe.db.sql(
		"UPDATE `tabDeploy` SET build=%s WHERE candidate=%s",
		(deploy_candidate_build_name, deploy_candidate_name),
	)
	frappe.db.sql(
		"UPDATE `tabBench` SET build=%s WHERE candidate=%s",
		(deploy_candidate_build_name, deploy_candidate_name),
	)


def is_valid_migration(without_builds: list[CandidateInfo]) -> bool:
	"""Check if the number of deploy candidate builds created is same as the number
	of deploy candidate that did not have a deploy candidate build.
	"""
	is_valid = False
	num_created_deploy_candidate_build = frappe.db.count(
		"Deploy Candidate Build",
		{"deploy_candidate": ("in", [candidate["deploy_candidate"] for candidate in without_builds])},
	)

	if len(without_builds) == num_created_deploy_candidate_build:
		is_valid = True

	return is_valid


def paginate(total_items, chunk_size):
	total_items += 1  # Inclusive range
	chunk_size += 1  # Inclusive range
	pages = []
	start = 0
	while start < total_items:
		end = min(start + chunk_size - 1, total_items - 1)
		pages.append((start, end))
		start = end + 1
	return pages


def execute():
	CHUNK_SIZE = 1000
	num_deploy_candidate_builds = frappe.db.count(
		"Deploy Candidate", {"status": ("not in", ["Draft", "Scheduled"])}
	)
	pages = paginate(num_deploy_candidate_builds, CHUNK_SIZE)
	total = len(pages)
	existing_deploy_candidate_builds = frappe.get_all(
		"Deploy Candidate Build", distinct=True, pluck="deploy_candidate"
	)
	for idx, (start, _) in enumerate(pages):
		print(f"In step: {idx}/{total}")
		start_time = time.time()
		deploy_candidates_info = get_deploy_bench_candidate(
			offset=start, limit=CHUNK_SIZE, existing_deploy_candidate_builds=existing_deploy_candidate_builds
		)

		for deploy_candidate_info in deploy_candidates_info:
			deploy_candidate_build_name = create_deploy_candidate_build(deploy_candidate_info)
			update_build_step_parent(deploy_candidate_info["deploy_candidate"], deploy_candidate_build_name)

		if not is_valid_migration(deploy_candidates_info):
			raise Exception("Migration Failed!")

		end_time = time.time()
		print(f"Time taken: {end_time - start_time}s")

		frappe.db.commit()
