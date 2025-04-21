# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt


"""
- Take cognizance of deploy candidate bench and deploy as well (get_Deploy_bench_candidate).
- For all deploy candidate make a deploy candidate build (create_deploy_candidate_build).
- Copy all build steps from deploy candidate to deploy candidate build (update_build_step_parent).

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
	"""Fetch all deploy candidates and their corresponding bench and deploy"""
	return (
		frappe.qb.from_(DeployCandidate)
		.select(
			(DeployCandidate.id).as_("deploy_candidate"),
			(DeployCandidate.group).as_("deploy_candidate_group"),
			(DeployCandidate.team).as_("deploy_candidate_team"),
			(DeployCandidate.status).as_("deploy_candidate_status"),
			(DeployCandidate.docker_image).as_("deploy_candidate_docker_image"),
			(DeployCandidate.docker_image_repository).as_("deploy_candidate_docker_image_repository"),
			(DeployCandidate.docker_image_id).as_("deploy_candidate_docker_image_id"),
			(DeployCandidate.docker_image_tag).as_("deploy_candidate_docker_image_tag"),
			(DeployCandidate.build_error).as_("deploy_candidate_build_error"),
			(DeployCandidate.build_output).as_("deploy_candidate_build_output"),
			(Bench.name).as_("bench"),
			(Deploy.name).as_("deploy"),
		)
		.where(DeployCandidate.build_output.isnotnull())
		.join(Bench)
		.on(Bench.candidate == DeployCandidate.name)
		.join(Deploy)
		.on(Deploy.candidate == DeployCandidate.name)
		.run(as_dict=True)
	)


def create_deploy_candidate_build(deploy_candidate: CandidateInfo) -> str:
	"""Create deploy candidate build for each deploy candidate"""
	deploy_candidate_build = frappe.new_doc(
		"Deploy Candidate Build",
		{
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
		},
	).insert(ignore_permissions=True)
	return deploy_candidate_build.name


def update_build_step_parent(deploy_candidate_name: str, deploy_candidate_build_name: str):
	"""Copy build step parent to deploy candidate build"""
	doc_updates = {}
	build_steps = frappe.get_all(
		"Deploy Candidate Build Step", {"parent": deploy_candidate_name}, pluck="name"
	)

	for build_step in build_steps:
		doc_updates[build_step] = {"parent": deploy_candidate_build_name}

	frappe.db.bulk_update("Deploy Candidate Build Step", doc_updates)


def add_deploy_and_bench_to_build(bench_name: str, deploy_name: str, deploy_candidate_build_name: str):
	"""Add build to deploy and bench if they exist"""
	bench = None
	deploy = None

	if bench_name:
		bench = frappe.get_doc("Bench", bench)
		bench.build = deploy_candidate_build_name
		bench.save()

	if deploy_name:
		deploy = frappe.get_doc("Deploy", deploy_name)
		deploy.build = deploy_candidate_build_name
		deploy.save()


def main():
	deploy_candidates_info = get_deploy_bench_candidate()

	for deploy_candidate_info in deploy_candidates_info:
		deploy_candidate_build_name = create_deploy_candidate_build(deploy_candidate_info)
		update_build_step_parent(deploy_candidate_info["deploy_candidate"], deploy_candidate_build_name)
		add_deploy_and_bench_to_build(
			deploy_candidate_info["bench"], deploy_candidate_info["deploy"], deploy_candidate_build_name
		)


if __name__ == "__main__":
	main()
