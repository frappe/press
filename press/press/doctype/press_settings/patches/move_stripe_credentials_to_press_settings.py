import frappe


def execute():
	from frappe.utils.password import get_decrypted_password, set_encrypted_password

	stripe_account = frappe.db.get_single_value("Press Settings", "stripe_account")

	# Fetch credentials from "Stripe Settings" doctype
	secret_key = get_decrypted_password("Stripe Settings", stripe_account, "secret_key")
	publishable_key = frappe.db.get_value(
		"Stripe Settings", stripe_account, "publishable_key"
	)

	frappe.reload_doctype("Press Settings")

	# Set credentials in Press Settings
	frappe.db.set_single_value("Press Settings", "stripe_publishable_key", publishable_key)
	set_encrypted_password(
		"Press Settings", "Press Settings", secret_key, "stripe_secret_key"
	)
