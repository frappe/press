import frappe
from .hmac_validator import HMACValidator
from press.utils import log_error

@frappe.whitelist(allow_guest=True)
def paymob_callback_handler():
	current_user = frappe.session.user
	form_dict = frappe.local.form_dict
	query_params = frappe.local.request.args

	try:
		payload = frappe.request.get_data(as_text=True) or ""
		payload = frappe.parse_json(payload)
		is_hmac_valid = HMACValidator(query_params.get("hmac"), frappe.parse_json(payload)).is_valid

		if not is_hmac_valid:
			raise Exception("Invalid HMAC value")

		# set user to Administrator, to not have to do ignore_permissions everywhere
		frappe.set_user("Administrator")

		paymob_order = frappe.db.exists("Paymob Log", {"event_type": "v1/intention", "special_reference": payload.get("obj", {}).get("order", {}).get("merchant_order_id")})

		if not paymob_order:
			log_error(
					"Paymob payment record for given order does not exist",
					special_reference=payload.get("obj", {}).get("order", {}).get("merchant_order_id"),
				)
			return

		frappe.get_doc(
				doctype="Paymob Callback Log",
				payload=frappe.as_json(payload),
				event_type=payload.get("type"),
				transaction_id=payload.get("obj", {}).get("id"),
				order_id=payload.get("obj", {}).get("payment_key_claims", {}).get("order_id"),
				special_reference=payload.get("obj", {}).get("order", {}).get("merchant_order_id")
			).insert(ignore_if_duplicate=True)

	except Exception as e:
		frappe.db.rollback()
		log_error(
			title="Paymob Callback Handler",
			transaction_id=form_dict.get("obj", {}).get("id"),
			order_id=form_dict.get("obj", {}).get("order"),
			special_reference=form_dict.get("obj", {}).get("order", {}).get("merchant_order_id")
		)
		frappe.set_user(current_user)
		raise


@frappe.whitelist(allow_guest=True)
def paymob_response_callback(**kwargs):
	query_params = frappe.local.request.args

	transaction_status = query_params.get('success')
	order_id = query_params.get('order')
	transaction_id = query_params.get('id')
	# TODO validate hmac
	# is_hmac_valid = HMACValidator(query_params.get("hmac"), frappe.parse_json(query_params)).is_valid
	
	# Determine the message to display based on the payment status
	if transaction_status == 'true':
		title = "Thank you"
		message = f"Payment was successful! Your Order ID is {order_id} and Transaction ID is {transaction_id}."
		indicator_color = "green"
	else:
		title = "Payment failed"
		message = f"Payment failed. Please try again or contact support with Order ID {order_id}."
		indicator_color = "red"
	
	return frappe.redirect_to_message(title, message, indicator_color=indicator_color)

