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
		is_hmac_valid = HMACValidator(query_params.get("hmac"), payload).is_valid

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
				special_reference=payload.get("obj", {}).get("order", {}).get("merchant_order_id"),
				success=payload.get("obj", {}).get("success")
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
    """
    Handle Paymob payment response callback, validate HMAC, and redirect with appropriate message.
    """
    try:
        query_params = get_query_params()
        transaction_status = query_params.get("success")
        order_id = query_params.get("order", {}).get("id")
        transaction_id = query_params.get("id")

        if transaction_status is None or order_id is None or transaction_id is None:
            frappe.log_error("Paymob Missing transaction parameters", f"Paymob Response Callback Error\n {query_params}")
            return frappe.redirect_to_message(
                title="Payment Error",
                html="Required transaction parameters are missing.",
                indicator_color="red"
            )

        # Validate HMAC to ensure data integrity
        is_hmac_valid = validate_hmac(query_params)
        if not is_hmac_valid:
            frappe.log_error("Paymob HMAC validation failed", f"Paymob Response Callback Error\n {query_params}")
            return frappe.redirect_to_message(
                title="Payment Error",
                html="Invalid transaction signature. Possible tampering detected.",
                indicator_color="red"
            )

        # Get the response message based on the transaction status and HMAC validation
        response_message = get_response_message(transaction_status, is_hmac_valid, order_id, transaction_id)

    except Exception as e:
        # Log the error and redirect to a generic error message
        frappe.log_error(f"Paymob Unexpected error: {str(e)}", "Paymob Response Callback Error")
        response_message = {
            "title": "Payment Processing Error",
            "html": "An unexpected error occurred while processing your payment. Please try again.",
            "indicator_color": "red"
        }

    return frappe.redirect_to_message(**response_message)



def get_query_params():
    """
    Retrieve and parse query parameters from the request.
    """
    query_params = frappe.local.request.args
    query_params = frappe.parse_json(query_params)

    # Update nested data structure for order and source_data, to validated HMAC
    query_params.update({
        "order": {"id": query_params.get("order")},
        "source_data": {
            "pan": query_params.get("source_data.pan"),
            "type": query_params.get("source_data.type"),
            "sub_type": query_params.get("source_data.sub_type"),
        },
    })
    return query_params


def validate_hmac(query_params):
    """
    Validate the HMAC for the given query parameters.
    """
    call_back_dict = frappe._dict({
        "type": "TRANSACTION",
        "obj": frappe.parse_json(query_params),
    })
    hmac_value = query_params.get("hmac")
    return HMACValidator(hmac_value, call_back_dict).is_valid


def get_response_message(transaction_status, is_hmac_valid, order_id, transaction_id):
    """
    Generate a response message based on the payment status and HMAC validation.
    """
    if transaction_status == "true" and is_hmac_valid:
        title = "Thank you"
        message = f"Payment was successful! Your Order ID is {order_id} and Transaction ID is {transaction_id}."
        indicator_color = "green"
    else:
        title = "Payment failed"
        message = f"Payment failed. Please try again or contact support with Order ID {order_id}."
        indicator_color = "red"

    return {"title": title, "html": message, "indicator_color": indicator_color}

