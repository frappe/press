# -*- coding: utf-8 -*-
# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt


import frappe

from press.api.site import protected
from frappe.utils import unique


@frappe.whitelist()
@protected("Stack")
def get(name):
	group = frappe.get_doc("Stack", name)
	return {
		"name": group.name,
		"title": group.title,
		"status": get_stack_status(name),
		"last_updated": group.modified,
		"creation": group.creation,
		"stack_tags": [],
		"tags": [],
	}


def get_stack_status(name):
	active_containers = frappe.get_all(
		"Container", {"stack": name, "status": "Active"}, limit=1, order_by="creation desc"
	)

	return "Active" if active_containers else "Awaiting Deploy"


@frappe.whitelist()
def all():
	stack = frappe.qb.DocType("Stack")
	query = (
		frappe.qb.from_(stack)
		.groupby(stack.name)
		.select(
			stack.name,
			stack.title,
			stack.creation,
		)
		.orderby(stack.title, order=frappe.qb.desc)
	)

	stacks = query.run(as_dict=True)

	if not stacks:
		return []

	for stack in stacks:
		stack.status = get_stack_status(stack.name)

	return stacks


@frappe.whitelist()
@protected("Stack")
def services(name):
	stack = frappe.get_doc("Stack", name)
	services = []
	deployed_services = frappe.db.get_all(
		"Container",
		filters={"stack": stack.name, "status": ("!=", "Archived")},
		pluck="service",
	)
	deployed_services = unique(deployed_services)

	for service in stack.services:
		service = frappe.get_doc("Service", service.service)
		services.append(
			{
				"name": service.name,
				"title": service.title,
				"image": service.image,
				"tag": service.tag,
				"deployed": service.name in deployed_services,
			}
		)
	return services


@frappe.whitelist()
@protected("Stack")
def deployments(filters=None, order_by=None, limit_start=None, limit_page_length=None):
	return frappe.get_all(
		"Deployment",
		["name", "creation", "status"],
		{"stack": filters["stack"], "status": ("!=", "Draft")},
		order_by=order_by or "creation desc",
		start=limit_start,
		limit=limit_page_length,
	)


@frappe.whitelist()
def deployment(name):
	deployment = frappe.get_doc("Deployment", name)
	containers = frappe.get_all("Container", ["name", "service"], {"deployment": name})
	jobs = []
	for container in containers:
		job = frappe.get_all(
			"Agent Job",
			["name", "status", "start", "end", "duration", "creation", "modified"],
			{"container": container.name, "job_type": "New Container"},
			limit=1,
		)[0]
		job.service = frappe.db.get_value("Service", container.service, "title")
		jobs.append(job)

	start = min([job.creation for job in jobs])
	end = max([job.modified for job in jobs])
	return {
		"name": deployment.name,
		"status": deployment.status,
		"creation": deployment.creation,
		"deployed": False,
		"containers": deployment.containers,
		"start": start,
		"end": end,
		"duration": (end - start),
		"jobs": jobs,
	}


@frappe.whitelist()
@protected("Stack")
def deploy_information(name):
	stack = frappe.get_doc("Stack", name)
	return stack.deploy_information()


@frappe.whitelist()
@protected("Stack")
def deploy(name):
	return frappe.get_doc("Stack", name).deploy()


@frappe.whitelist()
def stack_tags():
	return []
