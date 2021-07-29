# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import get_url

EXPIRES_IN_MINUTES = 10

class UserLogin(Document):
	def before_insert(self):
		if not frappe.db.exists("User", self.email):
			frappe.throw("No registered account with this email address")

		self.token = frappe.generate_hash("User Login", 20)
		self.code = frappe.generate_hash("User Login", 6).upper()
		self.expires_on = frappe.utils.add_to_date(None, minutes=EXPIRES_IN_MINUTES)
		self.ip = frappe.local.request_ip

	def after_insert(self):
		self.send_email()

	def send_email(self):
		link = self.get_link()
		if frappe.conf.developer_mode:
			print(f"\nVerification link for login via {self.email}")
			print(link)
			print()
			# return

		frappe.sendmail(
			subject="Login to Frappe Cloud",
			recipients=self.email,
			template="login_via_email",
			args={"link": link, "minutes": EXPIRES_IN_MINUTES, "code": self.code},
			now=True,
		)

	def verify(self):
		self.status  = "Verified"
		self.save(ignore_permissions=True)
		frappe.publish_realtime(f'user_login:{self.code}', 'success', after_commit=True)
		frappe.db.commit()

	def login(self):
		self.status = "Success"
		self.save(ignore_permissions=True)
		frappe.local.login_manager.login_as(self.email)
		frappe.db.commit()

	def get_link(self):
		return get_url(f"/api/method/press.api.account.verify_email_login?token={self.token}")
