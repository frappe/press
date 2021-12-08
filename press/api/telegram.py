# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

import frappe
from press.telegram_utils import Telegram
from press.utils import log_error


@frappe.whitelist(allow_guest=True, xss_safe=True)
def hook(*args, **kwargs):
	try:
		# set user to Administrator, to not have to do ignore_permissions everywhere
		frappe.set_user("Administrator")

		client = Telegram()
		client.respond(kwargs["message"])

	except Exception:
		log_error("Telegram Webhook Error", args=args, kwargs=kwargs)
	finally:
		frappe.set_user("Guest")
