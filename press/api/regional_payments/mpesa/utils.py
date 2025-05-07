import json
from datetime import datetime

import frappe
import requests
from frappe import _
from frappe.query_builder import DocType
from frappe.utils.password import get_decrypted_password

from press.utils import get_current_team

supported_mpesa_currencies = ["KES"]


@frappe.whitelist()
def update_mpesa_setup(mpesa_details):
	"""Create Mpesa Settings for the team."""
	mpesa_info = frappe._dict(mpesa_details)
	team = get_current_team()
	try:
		if not frappe.db.exists("Mpesa Setup", {"team": team}):
			mpesa_setup = frappe.get_doc(
				{
					"doctype": "Mpesa Setup",
					"team": team,
					"mpesa_setup_id": mpesa_info.mpesa_setup_id,
					"api_type": "Mpesa Express",
					"consumer_key": mpesa_info.consumer_key,
					"consumer_secret": mpesa_info.consumer_secret,
					"business_shortcode": mpesa_info.short_code,
					"till_number": mpesa_info.till_number,
					"pass_key": mpesa_info.pass_key,
					"security_credential": mpesa_info.security_credential,
					"initiator_name": mpesa_info.initiator_name,
					"sandbox": 1 if mpesa_info.sandbox else 0,
				}
			)

			mpesa_setup.insert(ignore_permissions=True)
		else:
			mpesa_setup = frappe.get_doc("Mpesa Setup", {"team": team})
			mpesa_setup.mpesa_setup_id = mpesa_info.mpesa_setup_id
			mpesa_setup.consumer_key = mpesa_info.consumer_key
			mpesa_setup.consumer_secret = mpesa_info.consumer_secret
			mpesa_setup.business_shortcode = mpesa_info.short_code
			mpesa_setup.till_number = mpesa_info.till_number
			mpesa_setup.pass_key = mpesa_info.pass_key
			mpesa_setup.security_credential = mpesa_info.security_credential
			mpesa_setup.initiator_name = mpesa_info.initiator_name
			mpesa_setup.sandbox = 1 if mpesa_info.sandbox else 0
			mpesa_setup.save()
			mpesa_setup.reload()

		return mpesa_setup.name
	except Exception as e:
		frappe.log_error(
			message=f"Error creating Mpesa Settings: {e!s}", title="MPesa Settings Creation Error"
		)
		return None


@frappe.whitelist()
def fetch_mpesa_setup():
	team = get_current_team()
	if frappe.db.exists("Mpesa Setup", {"team": team}):
		mpesa_setup = frappe.get_doc("Mpesa Setup", {"team": team})
		return {
			"mpesa_setup_id": mpesa_setup.mpesa_setup_id,
			"consumer_key": mpesa_setup.consumer_key,
			"consumer_secret": mpesa_setup.consumer_secret,
			"business_shortcode": mpesa_setup.business_shortcode,
			"till_number": mpesa_setup.till_number,
			"pass_key": mpesa_setup.pass_key,
			"initiator_name": mpesa_setup.initiator_name,
			"security_credential": mpesa_setup.security_credential,
			"api_type": mpesa_setup.api_type,
		}
	return None


@frappe.whitelist()
def display_invoices_by_partner():
	"""Display the list of invoices by partner."""
	team = get_current_team()
	invoices = frappe.get_all(
		"Mpesa Payment Record",
		filters={"team": team},
		fields=[
			"name",
			"posting_date",
			"amount",
			"local_invoice",
			"payment_partner",
			"amount_usd",
			"exchange_rate",
		],
	)
	return invoices  # noqa: RET504


@frappe.whitelist()
def get_exchange_rate(from_currency, to_currency):
	"""Get the latest exchange rate for the given currencies."""
	exchange_rate = frappe.db.get_value(
		"Currency Exchange",
		{"from_currency": from_currency, "to_currency": to_currency},
		"exchange_rate",
		order_by="creation DESC",
	)
	return exchange_rate  # noqa: RET504


@frappe.whitelist()
def update_payment_gateway_settings(gateway_details):
	"""Create Payment Gateway Settings for the team."""
	team = get_current_team()
	gateway_data = frappe._dict(gateway_details)

	try:
		if frappe.db.exists("Payment Gateway", {"team": team}):
			payment_gateway = frappe.get_doc("Payment Gateway", {"team": team})
			payment_gateway.update(
				{
					"gateway": gateway_data.gateway_name,
					"currency": gateway_data.currency,
					"gateway_settings": gateway_data.gateway_setting,
					"gateway_controller": gateway_data.gateway_controller,
					"url": gateway_data.url,
					"api_key": gateway_data.api_key,
					"api_secret": gateway_data.api_secret,
					"taxes_and_charges": gateway_data.taxes_and_charges,
					"print_format": gateway_data.print_format,
				}
			)
			return payment_gateway.save().name
		payment_gateway_settings = frappe.get_doc(
			{
				"doctype": "Payment Gateway",
				"team": team,
				"gateway": gateway_data.gateway_name,
				"currency": gateway_data.currency,
				"gateway_settings": gateway_data.gateway_setting,
				"gateway_controller": gateway_data.gateway_controller,
				"url": gateway_data.url,
				"api_key": gateway_data.api_key,
				"api_secret": gateway_data.api_secret,
				"taxes_and_charges": gateway_data.taxes_and_charges,
				"print_format": gateway_data.print_format,
			}
		)

		payment_gateway_settings.insert(ignore_permissions=True)
		return payment_gateway_settings
	except Exception as e:
		frappe.log_error(
			message=f"Error creating Payment Gateway Settings: {e!s}",
			title="Payment Gateway Settings Creation Error",
		)
		return None


@frappe.whitelist()
def get_payment_gateway_details():
	team = get_current_team()
	if frappe.db.exists("Payment Gateway", {"team": team}):
		payment_gateway = frappe.get_doc("Payment Gateway", {"team": team})
		return {
			"gateway_name": payment_gateway.gateway,
			"currency": payment_gateway.currency,
			"gateway_settings": payment_gateway.gateway_settings,
			"gateway_controller": payment_gateway.gateway_controller,
			"url": payment_gateway.url,
			"api_key": payment_gateway.api_key,
			"api_secret": payment_gateway.api_secret,
			"taxes_and_charges": payment_gateway.taxes_and_charges,
			"print_format": payment_gateway.print_format,
		}
	return None


@frappe.whitelist()
def get_gateway_controller():
	# """Get the list of controllers for the given doctype."""
	team = get_current_team(get_doc=True)
	gateway_setting = "Mpesa Setup" if team.country == "Kenya" else None
	if gateway_setting:
		return frappe.db.get_value(gateway_setting, {"team": team.name}, "name")
	return None


@frappe.whitelist()
def get_tax_percentage(payment_partner):
	team = frappe.db.get_value("Team", {"user": payment_partner}, "name")
	mpesa_setups = frappe.get_all(
		"Mpesa Setup", {"api_type": "Mpesa Express", "team": team}, pluck="name"
	)
	taxes_and_charges = 0
	for mpesa_setup in mpesa_setups:
		payment_gateways = frappe.get_all(
			"Payment Gateway",
			filters={"gateway_settings": "Mpesa Setup", "gateway_controller": mpesa_setup},
			fields=["taxes_and_charges"],
		)
		if payment_gateways:
			taxes_and_charges = payment_gateways[0].taxes_and_charges
			break  # we don't need the loop entirely
	return taxes_and_charges


def update_tax_id_or_phone_no(team, tax_id, phone_number):
	"""Update the tax ID or phone number for the team, only if they are different from existing values."""
	team_doc = frappe.get_doc("Team", team)

	# Check if updates are needed
	new_tax_id = tax_id and team_doc.mpesa_tax_id != tax_id
	new_phone_number = phone_number and team_doc.mpesa_phone_number != phone_number

	# Update only if at least one value needs updating
	if new_tax_id or new_phone_number:
		if tax_id:
			team_doc.mpesa_tax_id = tax_id
		if phone_number:
			team_doc.mpesa_phone_number = phone_number
		team_doc.save()


@frappe.whitelist()
def display_mpesa_payment_partners():
	"""Display the list of partners in the system with Mpesa integration enabled."""

	Team = DocType("Team")
	MpesaSetup = DocType("Mpesa Setup")

	query = (
		frappe.qb.from_(Team)
		.join(MpesaSetup)
		.on(Team.name == MpesaSetup.team)
		.select(Team.user)
		.where(Team.country == "Kenya")  # (MpesaSetup.sandbox == 1)
	)

	mpesa_partners = query.run(as_dict=True)

	return [partner["user"] for partner in mpesa_partners]


@frappe.whitelist()
def display_payment_partners():
	"""Display the list of partners in the system."""
	Team = DocType("Team")
	query = frappe.qb.from_(Team).select(Team.user).where(Team.erpnext_partner == 1)

	partners = query.run(as_dict=True)

	return [partner["user"] for partner in partners]


@frappe.whitelist()
def display_payment_gateway():
	"""Display the payment gateway for the partner."""
	gateways = frappe.get_all("Payment Gateway", filters={}, fields=["gateway"])
	return [gateway["gateway"] for gateway in gateways]


def get_details_from_request_log(transaction_id):
	"""Get the team and partner associated with the Mpesa Request Log."""
	request_log = frappe.get_doc("Mpesa Request Log", {"request_id": transaction_id, "status": "Queued"})
	request_data = request_log.data
	team = partner = None
	# Parse the request_data as a dictionary
	if request_data:
		try:
			request_data_dict = json.loads(request_data)
			team = request_data_dict.get("team")
			partner_ = request_data_dict.get("partner")
			partner = frappe.get_value("Team", {"user": partner_, "erpnext_partner": 1, "enabled": 1}, "name")
			requested_amount = request_data_dict.get("request_amount")
			amount_usd = request_data_dict.get("amount_usd")
			exchange_rate = request_data_dict.get("exchange_rate")
		except json.JSONDecodeError:
			frappe.throw(_("Invalid JSON format in request_data"))
			team = None
			partner = None

	return frappe._dict(
		{
			"team": team,
			"partner": partner,
			"requested_amount": requested_amount,
			"amount_usd": amount_usd,
			"exchange_rate": exchange_rate,
		}
	)


def get_payment_gateway(partner_value):
	"""Get the payment gateway for the partner."""
	partner = frappe.get_doc("Team", partner_value)
	mpesa_setup = get_mpesa_setup_for_team(partner.name)
	payment_gateway = frappe.get_all(
		"Payment Gateway",
		filters={"gateway_settings": "Mpesa Setup", "gateway_controller": mpesa_setup.name},
		pluck="name",
	)
	if not payment_gateway:
		frappe.throw(_("Payment Gateway not found"), title=_("Mpesa Express Error"))
	gateway = frappe.get_doc("Payment Gateway", payment_gateway[0])
	return gateway.name


def get_mpesa_setup_for_team(team_name):
	"""Fetch Mpesa setup for a given team."""

	mpesa_setup = frappe.get_all("Mpesa Setup", {"team": team_name}, pluck="name")
	if not mpesa_setup:
		frappe.throw(
			_(f"Mpesa Setup not configured for the team {team_name}"), title=_("Mpesa Express Error")
		)
	return frappe.get_doc("Mpesa Setup", mpesa_setup[0])


def sanitize_mobile_number(number):
	"""ensures number take the right format"""
	"""Add country code and strip leading zeroes from the phone number."""
	return "254" + str(number).lstrip("0")


def fetch_param_value(response, key, key_field):
	"""Fetch the specified key from list of dictionary. Key is identified via the key field."""
	for param in response:
		if param[key_field] == key:
			return param["Value"]
	return None


@frappe.whitelist()
def create_exchange_rate(**kwargs):
	"""Create a new exchange rate record."""
	try:
		from_currency = kwargs.get("from_currency", {}).get("value")
		to_currency = kwargs.get("to_currency", {}).get("value")
		exchange_rate = kwargs.get("exchange_rate")

		if not from_currency or not to_currency or not exchange_rate:
			raise ValueError("Missing required fields.")

		exchange_rate_doc = frappe.get_doc(
			{
				"doctype": "Currency Exchange",
				"from_currency": from_currency,
				"to_currency": to_currency,
				"exchange_rate": exchange_rate,
				"date": frappe.utils.today(),
			}
		)

		exchange_rate_doc.insert(ignore_permissions=True)
		return exchange_rate_doc.name

	except Exception as e:
		frappe.log_error("Error creating exchange rate")
		raise e


def create_payment_partner_transaction(
	team, payment_partner, exchange_rate, amount, paid_amount, payment_gateway, payload=None
):
	"""Create a Payment Partner Transaction record."""
	transaction_doc = frappe.get_doc(
		{
			"doctype": "Payment Partner Transaction",
			"team": team,
			"payment_partner": payment_partner,
			"exchange_rate": exchange_rate,
			"payment_gateway": payment_gateway,
			"amount": amount,
			"actual_amount": paid_amount,
			"payment_transaction_details": payload,
		}
	)
	transaction_doc.insert(ignore_permissions=True)
	transaction_doc.submit()
	return transaction_doc.name


@frappe.whitelist()
def fetch_payments(payment_gateway, partner, from_date, to_date):
	partner = (
		partner if frappe.db.exists("Team", partner) else frappe.get_value("Team", {"user": partner}, "name")
	)
	filters = {
		"docstatus": 1,
		"submitted_to_frappe": 0,
		"payment_gateway": payment_gateway,
		"payment_partner": partner,
	}

	from_date = convert_string_to_date(from_date)
	to_date = convert_string_to_date(to_date)
	if from_date and to_date:
		filters["posting_date"] = ["between", [from_date, to_date]]

	partner_payments = frappe.get_all(
		"Payment Partner Transaction", filters=filters, fields=["name", "amount", "posting_date"]
	)
	print("Partner Payments", partner_payments)
	frappe.response.message = partner_payments
	return partner_payments


@frappe.whitelist()
def fetch_percentage_commission(partner):
	"""Fetch the percentage commission for the partner."""
	return frappe.get_value("Team", {"user": partner}, "partner_commission")


@frappe.whitelist()
def create_invoice_partner_site(data, gateway_controller):
	gateway = frappe.get_doc("Payment Gateway", gateway_controller)
	api_url_ = gateway.url
	api_key = gateway.api_key
	api_secret = get_decrypted_password("Payment Gateway", gateway.name, fieldname="api_secret")

	transaction_id = data.get("transaction_id")
	amount = data.get("amount")
	team = data.get("team")
	default_currency = data.get("default_currency")
	rate = data.get("rate")

	# Validate the necessary fields
	if not transaction_id or not amount:
		frappe.throw(_("Invalid transaction data received"))

	api_url = api_url_

	headers = {
		"Authorization": f"token {api_key}:{api_secret}",
	}
	# Define the payload to send with the POST request
	payload = {
		"transaction_id": transaction_id,
		"amount": amount,
		"team": team,
		"default_currency": default_currency,
		"rate": rate,
	}
	# Make the POST request to your API
	try:
		response = requests.post(api_url, data=payload, headers=headers)
		if response.status_code == 200:
			response_data = response.json()
			download_link = response_data.get("message", "")
			invoice_name = response_data.get("invoice_name", "")
			return download_link, invoice_name
		frappe.log_error(f"API Error: {response.status_code} - {response.text}")
		frappe.throw(_("Failed to create the invoice via API"))

	except requests.exceptions.RequestException as e:
		frappe.log_error(f"Error calling API: {e}")
		frappe.throw(_("There was an issue connecting to the API."))


@frappe.whitelist()
def display_payment_gateways(payment_partner):
	"""Display the list of payment gateways for the partner."""
	Team = DocType("Team")
	PaymentGateway = DocType("Payment Gateway")

	query = (
		frappe.qb.from_(Team)
		.join(PaymentGateway)
		.on(Team.name == PaymentGateway.team)
		.select(PaymentGateway.name)
		.where(Team.user == payment_partner)
	)

	payment_gateways = query.run(as_dict=True)

	return [gateway["name"] for gateway in payment_gateways]


@frappe.whitelist()
def fetch_payouts():
	team = get_current_team()
	payouts = frappe.get_all(
		"Partner Payment Payout",
		filters={"partner": team},
		fields=["name", "total_amount", "commission", "net_amount", "posting_date"],
	)
	print("here", len(payouts))
	return payouts


def convert_string_to_date(date_string):
	return datetime.strptime(date_string, "%Y-%m-%d").date()
