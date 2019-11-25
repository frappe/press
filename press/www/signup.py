from __future__ import unicode_literals
import frappe


no_cache = True


def get_context(context):
	if frappe.session.user != "Guest":
		frappe.local.flags.redirect_location = "dashboard"
		raise frappe.Redirect


@frappe.whitelist(allow_guest=True)
def signup(first_name, last_name, email, password):
	request = create_account_request(first_name, last_name, email, password)
	if request:
		login_as_new_user(email, password)


def create_account_request(first_name, last_name, email, password):
	try:
		request_dict = {
			"doctype": "Account Request",
			"first_name": first_name,
			"last_name": last_name,
			"email": email,
			"password": password,
			"ip": frappe.local.request_ip,
		}
		account_request = frappe.get_doc(request_dict)
		account_request.insert(ignore_permissions=True)
		return account_request
	except Exception:
		message = "first_name: {}, last_name: {}, email: {}\n{}".format(
			first_name, last_name, email, frappe.get_traceback()
		)
		frappe.log_error(title="Account Request Creation Error", message=message)


def login_as_new_user(email, password):
	frappe.local.form_dict.usr = email
	frappe.local.form_dict.pwd = password
	frappe.local.login_manager.login()
