# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt
import frappe


def execute():
	DOCTYPES = ["Server", "Database Server"]
	for doctype in DOCTYPES:
		server_names = frappe.get_all(
			doctype,
			{"status": ("!=", "Archived"), "virtual_machine": ("is", "set")},
			pluck="name",
		)
		for server_name in server_names:
			server = frappe.get_doc(doctype, server_name)

			subscription = frappe.get_all(
				"Subscription", ["name", "plan"], {"enabled": True, "document_name": server.name}
			)

			if subscription and server.plan:
				# Plan is set and an active subscription exists
				# Nothing to do here
				continue
			if subscription and not server.plan:
				# Subscription exists but plan is not set
				# Set Server.plan to the plan of the subscription
				print(
					f"Subscription exists, but plan isn't set for {doctype} {server.name} setting plan to {subscription[0].plan}"
				)
				server.plan = subscription[0].plan
				server.save()
			if not subscription and server.plan:
				# Plan is set but no subscription exists
				# Create a subscription
				print(
					f"Plan is set but no subscription exists for {doctype} {server.name} creating subscription for {server.plan}"
				)
				server.create_subscription(server.plan)
			if not subscription and not server.plan:
				# Plan is not set and no subscription exists
				# Find a plan based on the server's instance type
				instance_type = frappe.db.get_value("Virtual Machine", server.virtual_machine, "machine_type")
				plan = frappe.get_all(
					"Server Plan",
					{
						"enabled": True,
						"server_type": doctype,
						"cluster": server.cluster,
						"instance_type": instance_type,
						"premium": False,
					},
				)
				if plan:
					print(
						f"Found plan for {doctype} {server.name} based on instance_type {instance_type} setting plan to {plan}"
					)
					server.plan = plan[0].name
					server.save()
					server.create_subscription(server.plan)
				else:
					instance_type = instance_type.replace("7", "6")
					instance_type = instance_type.replace("5", "6i")
					plan = frappe.get_all(
						"Server Plan",
						{
							"enabled": True,
							"server_type": doctype,
							"cluster": server.cluster,
							"instance_type": instance_type,
							"premium": False,
						},
					)

					print(
						f"No exact match plan found for {doctype} {server.name} based on instance_type {instance_type} found next best plan {plan[0].name}"
					)
					server.plan = plan[0].name
					server.save()
					server.create_subscription(server.plan)
