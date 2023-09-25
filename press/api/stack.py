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
