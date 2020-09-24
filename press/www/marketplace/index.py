# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# Proprietary License. See license.txt

from __future__ import unicode_literals
import frappe
from press.api.app import marketplace_apps


def get_context(context):
	context.apps = marketplace_apps()
