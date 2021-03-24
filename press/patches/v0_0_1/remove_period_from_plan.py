# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

import frappe


def execute():
	frappe.db.sql_ddl("ALTER TABLE `tabPlan` DROP COLUMN `period`")
