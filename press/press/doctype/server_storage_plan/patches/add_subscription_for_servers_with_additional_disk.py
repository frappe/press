# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt


import frappe
from tqdm import tqdm


def execute():
	Server = frappe.qb.DocType("Server")
	DatabaseServer = frappe.qb.DocType("Database Server")
	VirtualMachine = frappe.qb.DocType("Virtual Machine")
	ServerPlan = frappe.qb.DocType("Server Plan")

	servers = (
		frappe.qb.from_(Server)
		.select(Server.name, Server.team, ServerPlan.disk, VirtualMachine.disk_size)
		.join(VirtualMachine)
		.on(Server.virtual_machine == VirtualMachine.name)
		.join(ServerPlan)
		.on(Server.plan == ServerPlan.name)
		.where(ServerPlan.disk < VirtualMachine.disk_size)
		.where(Server.public == 0)
		.run(as_dict=True)
	)

	database_servers = (
		frappe.qb.from_(DatabaseServer)
		.select(
			DatabaseServer.name, DatabaseServer.team, ServerPlan.disk, VirtualMachine.disk_size
		)
		.join(VirtualMachine)
		.on(DatabaseServer.virtual_machine == VirtualMachine.name)
		.join(ServerPlan)
		.on(DatabaseServer.plan == ServerPlan.name)
		.where(ServerPlan.disk < VirtualMachine.disk_size)
		.where(DatabaseServer.public == 0)
		.run(as_dict=True)
	)

	for server in tqdm(servers):
		frappe.get_doc("Server", server.name).create_subscription_for_storage()

	for database_server in tqdm(database_servers):
		frappe.get_doc(
			"Database Server", database_server.name
		).create_subscription_for_storage()
