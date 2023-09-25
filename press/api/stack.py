# -*- coding: utf-8 -*-
# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt


import frappe


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
def stack_tags():
	return []
