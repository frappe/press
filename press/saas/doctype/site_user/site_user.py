# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

import frappe
from frappe.model.document import Document


class SiteUser(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		enabled: DF.Check
		otp: DF.Data | None
		site: DF.Link | None
		user: DF.Data | None
	# end: auto-generated types

	def send_otp(self):
		"""Send OTP to the user for site login."""

		import random

		self.otp = random.randint(100000, 999999)
		self.save()

		if frappe.conf.developer_mode:
			print(f"\nOTP for {self.user} for product login:")
			print()
			print(self.otp)
			print()
			return

		subject = f"{self.otp} - OTP for Frappe Cloud Site Login"
		args = {}
		template = "verify_account_for_site_login"
		site = frappe.db.get_value("Site", self.site, ["name", "site_label"], as_dict=True)
		site = site.site_label or site.name

		args.update(
			{
				"otp": self.otp,
				"site": site,
				"image_path": "https://github.com/frappe/gameplan/assets/9355208/447035d0-0686-41d2-910a-a3d21928ab94",
			}
		)

		frappe.sendmail(
			recipients=self.user,
			subject=subject,
			template=template,
			args=args,
			now=True,
		)

	def verify_otp(self, otp):
		"""Verify OTP for site login."""
		if not self.otp:
			return frappe.throw("OTP is not set")
		if self.otp != otp:
			return frappe.throw("Invalid OTP")
		self.otp = None
		self.save()
		return True

	def login_to_site(self):
		"""Login to the site."""
		if not self.enabled:
			frappe.throw("User is disabled")

		# Get the site
		site = frappe.get_doc("Site", self.site)
		return site.login_as_user(self.user)


def create_user_for_product_site(site, data):
	analytics = data["analytics"]
	users_data = analytics.get("users", [])
	for user_data in users_data:
		user_mail = user_data.get("email")
		enabled = user_data.get("enabled")
		if frappe.db.exists("Site User", {"site": site, "user": user_mail}):
			user = frappe.db.get_value(
				"Site User", {"site": site, "user": user_mail}, ["name", "enabled"], as_dict=True
			)
			if user.enabled != enabled:
				frappe.db.set_value("Site User", user.name, "enabled", enabled)
		else:
			user = frappe.get_doc(
				{"doctype": "Site User", "site": site, "user": user_mail, "enabled": enabled}
			)
			user.insert()
