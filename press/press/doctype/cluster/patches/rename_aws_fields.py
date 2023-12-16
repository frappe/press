# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt

import frappe
from frappe.model.utils.rename_field import rename_field


def execute():
	frappe.reload_doctype("Cluster")
	rename_field("Cluster", "aws_vpc_id", "vpc_id")
	rename_field("Cluster", "aws_subnet_id", "subnet_id")
	rename_field("Cluster", "aws_proxy_security_group_id", "proxy_security_group_id")
	rename_field("Cluster", "aws_security_group_id", "security_group_id")
	rename_field("Cluster", "aws_route_table_id", "route_table_id")
	rename_field("Cluster", "aws_network_acl_id", "network_acl_id")
