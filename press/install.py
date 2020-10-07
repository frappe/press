# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import os

import frappe


def after_install():
	create_administrator_team()
	create_certificate_authorities()


def create_certificate_authorities():
	if not frappe.conf.developer_mode:
		return

	bench = frappe.utils.get_bench_path()
	scratch = os.path.join(bench, f"backbone-ca-{frappe.generate_hash(length=6)}")

	if not os.path.exists(scratch):
		os.mkdir(scratch)

	if frappe.db.count("Certificate Authority"):
		return

	root_ca = frappe.get_doc(
		{
			"doctype": "Certificate Authority",
			"common_name": "Backbone Root Certificate Authority",
			"is_root_ca": True,
			"directory": f"{scratch}/root",
		}
	).insert()
	intermediate_ca = frappe.get_doc(
		{
			"doctype": "Certificate Authority",
			"common_name": "Backbone Intermediate Certificate Authority",
			"parent_authority": root_ca.name,
			"directory": f"{scratch}/intermediate",
		}
	).insert()
	frappe.db.set_value(
		"Press Settings", "Press Settings", "backbone_intermediate_ca", intermediate_ca.name
	)


def create_administrator_team():
	administrator_team = frappe.get_doc(
		{
			"doctype": "Team",
			"name": "Administrator",
			"user": "Administrator",
			"enabled": 1,
			"free_account": 1,
			"team_members": [{"user": "Administrator"}],
		}
	)
	administrator_team.insert()
