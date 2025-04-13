# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

import frappe
from press.saas.api import whitelist_saas_api
from time import sleep

@whitelist_saas_api
def info():
    team = frappe.local.get_team()
    data = team.as_dict()
    team.get_doc(data)
    return data