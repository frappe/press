import frappe
from press.utils import get_current_team
from press.api.billing import total_unpaid_amount
from press.press.doctype.paymob_settings.accept_api import AcceptAPI
from frappe.model.naming import _generate_random_string

@frappe.whitelist()
def intent_to_buying_credits(amount, team, actualAmount):
	try:
		iframe = create_payment_intent_for_buying_credits(amount, team, actualAmount)
		return iframe
	except Exception as e:
		frappe.log_error("Intent to Buying Credits using Paymob", frappe.get_traceback(True))
		frappe.throw(e)
	

def create_payment_intent_for_buying_credits(amount, team, actualAmount):
	print(amount, team, actualAmount)
	# get current team details
	team = get_current_team(True)
	total_unpaid = total_unpaid_amount()

	if amount < total_unpaid and not team.erpnext_partner:
		frappe.throw(f"Amount {amount} is less than the total unpaid amount {total_unpaid}.")

	# create paymob log
	paymob_log = frappe.new_doc("Paymob Log")
	paymob_log.event_type = "v1/intention"
	paymob_log.payment_partner = team
	paymob_log.team = team.name

	# build payment_data payload
	payment_data = build_payment_data(team, amount=actualAmount)
	validate_billing_data(payment_data)
	paymob_log.special_reference = payment_data.get("special_reference")

	# create payment intention
	accept = AcceptAPI()
	intent = accept.create_payment_intent(payment_data)
	print(intent)

	# build iframe url
	iframe_url = None
	if intent.get("payment_keys"):
		paymob_log.payload = str(intent)
		iframe_url = accept.retrieve_iframe(accept.paymob_settings.iframe, intent["payment_keys"][0]["key"])
		paymob_log.insert(ignore_permissions=True)
		return iframe_url
		
	paymob_log.insert(ignore_permissions=True)

	# return iframe url to UI and rediret to it
	return iframe_url

def build_payment_data(team, amount):
	payment_integration_id = frappe.db.get_single_value("Paymob Settings", "payment_integration")
	address_details = team.billing_details()
	first_name, last_name = frappe.db.get_value("User", team.user, ["first_name", "last_name"])
	payment_data = {
		"amount": int(amount * 100),
		"currency": "EGP",
		"expiration": 5800,
		"payment_methods": [
			payment_integration_id,
			"card",
		],
		"items": [
			{
			"name": "Frappe PrePaid Crdit",
			"amount": int(amount * 100),
			"description": "Frappe Cloud Prepaid Credit",
			"quantity": 1
			}
		],
		"billing_data": {
			"apartment": "6", # TODO make it dynamic
			"first_name": first_name,
			"last_name": last_name,
			"street": address_details.get("address_line1") or address_details.get("address_line2"),
			"building": "939", # TODO make it dynamic
			"phone_number": address_details.get("phone"),
			"country": address_details.get("country"),
			"email": address_details.get("email_id"),
			"floor": "1", # TODO make it dynamic
			"state": address_details.get("state")
		},
		"special_reference": _generate_random_string().upper(),
		"customer": {
			"first_name": first_name,
			"last_name": last_name,
			"email": address_details.get("email_id"),
			"extras": {
				"re": "22"
			}
		},
		"extras": {
			"ee": 22
		}
	}

	return payment_data


def validate_billing_data(payment_data: dict):
	throw_msg = ""
	for key, value in payment_data.get("billing_data").items():
		if not value:
			throw_msg += f"Missing billing data <b>{key}</b><br>"
	if throw_msg:
		frappe.throw(throw_msg)

@frappe.whitelist()
def get_payment_getway(payment_getway):
	return frappe.get_doc("Payment Gateway", payment_getway).as_dict()