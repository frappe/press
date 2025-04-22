# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt


"""
- Take cognizance of deploy candidate bench and deploy as well (get_deploy_bench_candidate).
- For all deploy candidate make a deploy candidate build copied all build fields into deploy candidate build (create_deploy_candidate_build).
- Copy all build steps from deploy candidate to deploy candidate build (update_build_step_parent).
- Copy deploy candidate build name to all deploy and bench associated with it (add_deploy_and_bench_to_build).
"""

from __future__ import annotations

import typing

import frappe

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
	bench: str
	deploy: str


def get_deploy_bench_candidate() -> list[CandidateInfo]:
	"""Fetch all deploy candidates and their corresponding bench and deploy which don't have a build"""
	without_build_candidates = []
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
		.where(
			DeployCandidate.status.notin(["Draft", "Scheduled"])
		)  # We don't want to create a build for scheduled & draft deploy candidates
		.run(as_dict=True)
	)

	for deploy_candidate in deploy_candidates:
		if not frappe.get_value(
			"Deploy Candidate Build", {"deploy_candidate": deploy_candidate["deploy_candidate"]}
		):
			without_build_candidates.append(deploy_candidate)

	return without_build_candidates


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
			"run_after_insert": False,
		},
	).insert(ignore_permissions=True)
	add_build_to_deploy_and_bench(deploy_candidate["deploy_candidate"], deploy_candidate.name)
	return deploy_candidate_build.name


def update_build_step_parent(deploy_candidate_name: str, deploy_candidate_build_name: str):
	"""Copy build step parent to deploy candidate build"""
	doc_updates = {}
	build_steps = frappe.get_all(
		"Deploy Candidate Build Step",
		{"parent": deploy_candidate_name},
		pluck="name",
	)

	for build_step in build_steps:
		doc_updates[build_step] = {
			"parent": deploy_candidate_build_name,
			"parenttype": "Deploy Candidate Build",
		}

	frappe.db.bulk_update("Deploy Candidate Build Step", doc_updates)


def add_build_to_deploy_and_bench(deploy_candidate_name: str, deploy_candidate_build_name: str):
	"""Add build to deploy and bench if they exist"""
	frappe.db.set_value("Deploy", {"candidate": deploy_candidate_name}, "build", deploy_candidate_build_name)
	frappe.db.set_value("Bench", {"candidate": deploy_candidate_name}, "build", deploy_candidate_build_name)


def execute():
	deploy_candidates_info = get_deploy_bench_candidate()

	for deploy_candidate_info in deploy_candidates_info:
		deploy_candidate_build_name = create_deploy_candidate_build(deploy_candidate_info)
		update_build_step_parent(deploy_candidate_info["deploy_candidate"], deploy_candidate_build_name)

	frappe.db.commit()
