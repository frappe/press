
import requests
import frappe
from frappe.utils.password import get_decrypted_password

@frappe.whitelist(allow_guest=True)
def create_invoice_partner_site(data, gateway_controller):
	gateway=frappe.get_doc("Payment Gateway", gateway_controller)
	api_url_ = gateway.url
	api_key = gateway.api_key
	api_secret = get_decrypted_password("Payment Gateway", gateway.name, fieldname="api_secret")
	
	transaction_id = data.get("transaction_id")
	trans_amount = data.get("trans_amount")
	team = data.get("team")
	default_currency = data.get("default_currency")
	rate = data.get("rate")
	
	# Validate the necessary fields
	if not transaction_id or not trans_amount:
		frappe.throw(_("Invalid transaction data received"))

	api_url = api_url_

	headers = {
		"Authorization": f"token {api_key}:{api_secret}",
	}
	# Define the payload to send with the POST request
	payload = {
		"transaction_id": transaction_id,
		"trans_amount": trans_amount,
		"team": team,
		"default_currency": default_currency,
		"rate":rate
	}
	# Make the POST request to your API
	try:
		response = requests.post(api_url, data=payload, headers=headers)
		if response.status_code == 200:
			response_data = response.json()
			download_link = response_data.get("message", "")
			return download_link
		else:
			frappe.log_error(f"API Error: {response.status_code} - {response.text}")
			frappe.throw(_("Failed to create the invoice via API"))

	except requests.exceptions.RequestException as e:
		frappe.log_error(f"Error calling API: {e}")
		frappe.throw(_("There was an issue connecting to the API."))
