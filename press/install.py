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

	if frappe.db.count("Certificate Authority"):
		return

	bench = frappe.utils.get_bench_path()

	scratch_directory = os.path.join(bench, "scratch")
	if os.path.exists(scratch_directory):
		scratch_directory = f"{scratch_directory}-{frappe.generate_hash(length=6)}"

	os.mkdir(scratch_directory)

	ca_directory = os.path.join(scratch_directory, "ca")
	os.mkdir(ca_directory)

	root_ca = frappe.get_doc(
		{
			"doctype": "Certificate Authority",
			"common_name": "Backbone Root Certificate Authority",
			"is_root_ca": True,
			"directory": f"{ca_directory}/root",
		}
	).insert()
	intermediate_ca = frappe.get_doc(
		{
			"doctype": "Certificate Authority",
			"common_name": "Backbone Intermediate Certificate Authority",
			"parent_authority": root_ca.name,
			"directory": f"{ca_directory}/intermediate",
		}
	).insert()
	frappe.db.set_value(
		"Press Settings", "Press Settings", "backbone_intermediate_ca", intermediate_ca.name
	)
	frappe.db.set_value(
		"Press Settings", "Press Settings", "backbone_directory", scratch_directory
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
