# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe

def get_context(context):
	frappe.local.flags.redirect_location = '/dashboard/#/login'
	raise frappe.Redirect
