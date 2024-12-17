import frappe
from press.utils import get_current_team
from frappe.query_builder import DocType
import json
from frappe import _ 


supported_mpesa_currencies = ["KES"]


@frappe.whitelist(allow_guest=True)
def get_tax_id():
	"""Get the tax ID for the team."""
	team=get_current_team()
	team_doc = frappe.get_doc("Team", team)
	return team_doc.tax_id if team_doc.tax_id else ''

@frappe.whitelist(allow_guest=True)
def get_phone_no():
	"""Get the phone number for the team."""
	team=get_current_team()
	team_doc = frappe.get_doc("Team", team)
	return team_doc.phone_number if team_doc.phone_number else ''

@frappe.whitelist(allow_guest=True)
def display_invoices_by_partner():
	"""Display the list of invoices by partner."""
	team = get_current_team()
	invoices = frappe.get_all("Mpesa Payment Record", filters={"team":team}, fields=["name","posting_date", "trans_amount", "default_currency","local_invoice"])
	return invoices

@frappe.whitelist(allow_guest=True)
def get_exchange_rate(from_currency, to_currency):
	"""Get the latest exchange rate for the given currencies."""
	exchange_rate = frappe.db.get_value(
		"Currency Exchange",
		{"from_currency": from_currency, "to_currency": to_currency},
		"exchange_rate",
		order_by="creation DESC"  
	)
	return exchange_rate


@frappe.whitelist(allow_guest=True)
def create_payment_gateway_settings(**kwargs):
	"""Create Payment Gateway Settings for the team."""
	team = get_current_team() 
	args = frappe._dict(kwargs)

	try:

		payment_gateway_settings = frappe.get_doc({
			"doctype": "Payment Gateway",
			"team": team,
			"gateway": args.get("gateway_name"),
			"currency": args.get("currency"),
			"gateway_settings": args.get("gateway_setting"),
			"gateway_controller": args.get("gateway_controller"),
			"url": args.get("url"),
			"api_key": args.get("api_key"),
			"api_secret": args.get("api_secret"),
			"taxes_and_charges": args.get("taxes_and_charges"),
		})

		payment_gateway_settings.insert(ignore_permissions=True)
		frappe.db.commit()

		return payment_gateway_settings.name
	except Exception as e:
		frappe.log_error(message=f"Error creating Payment Gateway Settings: {str(e)}", title="Payment Gateway Settings Creation Error")
		return None

@frappe.whitelist(allow_guest=True)
def get_currency_options():
	"""Get the list of currencies supported by the system."""
	currencies=frappe.get_all("Currency", fields=["name"])
	names=[currency['name'] for currency in currencies]
	return names

@frappe.whitelist(allow_guest=True)
def get_gateway_settings():
	"""Get the list of doctypes supported by the system."""
	doctypes=frappe.get_all("DocType", fields=["name"])
	names=[doc['name'] for doc in doctypes]
	return names

@frappe.whitelist(allow_guest=True)
def get_gateway_controllers(gateway_setting):
	"""Get the list of controllers for the given doctype."""
	controllers = frappe.get_all(gateway_setting, fields=["name"])
	
	names = [doc['name'] for doc in controllers]
	
	return names 

@frappe.whitelist(allow_guest=True)
def get_tax_percentage(payment_partner):
	team_doc = frappe.get_doc("Team", {"user": payment_partner})
	mpesa_settings=frappe.get_all("Mpesa Settings", filters={"api_type":"Mpesa Express", "team":team_doc.name}, fields=["name"])
	for mpesa_setting in mpesa_settings:
		payment_gateways = frappe.get_all("Payment Gateway", filters={"gateway_settings":"Mpesa settings","gateway_controller":mpesa_setting }, fields=["taxes_and_charges"])
		if payment_gateways:
			taxes_and_charges = payment_gateways[0].taxes_and_charges
	return taxes_and_charges


def update_tax_id_or_phone_no(team, tax_id, phone_number):
	"""Update the tax ID or phone number for the team, only if they are different from existing values."""
	
	doc_name = frappe.get_value("Team", {"user": team}, "name")
	team_doc = frappe.get_doc("Team", doc_name)
	
	# Check if updates are needed
	tax_id_needs_update = tax_id and team_doc.tax_id != tax_id
	phone_number_needs_update = phone_number and team_doc.phone_number != phone_number

	# Update only if at least one value needs updating
	if tax_id_needs_update or phone_number_needs_update:
		if tax_id_needs_update:
			team_doc.tax_id = tax_id
		if phone_number_needs_update:
			team_doc.phone_number = phone_number
		team_doc.save()

  
def convert(from_currency, to_currency, amount):
	"""Convert the given amount from one currency to another."""
	exchange_rate = frappe.get_value("Currency Exchange", {"from_currency": from_currency, "to_currency": to_currency}, "exchange_rate")
	converted_amount = amount / exchange_rate
	return converted_amount, exchange_rate

@frappe.whitelist(allow_guest=True)
def display_mpesa_payment_partners():
	"""Display the list of partners in the system with Mpesa integration enabled."""
	
	Team = DocType("Team")
	MpesaSettings = DocType("Mpesa Settings")

	query = (
		frappe.qb.from_(Team)
		.join(MpesaSettings)
		.on(Team.name == MpesaSettings.team)
		.select(Team.user)
		.where((Team.country == "Kenya") ) #(MpesaSettings.sandbox == 1)
	)

	mpesa_partners = query.run(as_dict=True)

	return [partner['user'] for partner in mpesa_partners]

@frappe.whitelist(allow_guest=True)
def display_payment_partners():
	"""Display the list of partners in the system."""
	Team = DocType("Team")
	query = (
		frappe.qb.from_(Team)
		.select(Team.user)
		.where(Team.erpnext_partner == 1)
	)

	partners = query.run(as_dict=True)
	
	return [partner['user'] for partner in partners]

@frappe.whitelist(allow_guest=True)
def display_payment_gateway():
	"""Display the payment gateway for the partner."""
	gateways=frappe.get_all("Payment Gateway", filters={}, fields=["gateway"])
	return [gateway["gateway"] for gateway in gateways]

def get_team_and_partner_from_integration_request(transaction_id):
	"""Get the team and partner associated with the Mpesa Request Log."""
	integration_request = frappe.get_doc("Mpesa Request Log", transaction_id)
	request_data = integration_request.data
	# Parse the request_data as a dictionary
	if request_data:
		try:
			
			request_data_dict = json.loads(request_data)  
			team_ = request_data_dict.get("team")
			team = frappe.get_value("Team", {"user": team_}, "name")
			partner_ = request_data_dict.get("partner")
			partner = frappe.get_value("Team", {"user": partner_}, "name")
			requested_amount=request_data_dict.get("request_amount")
		except json.JSONDecodeError:
			frappe.throw(_("Invalid JSON format in request_data"))
			team = None
			partner = None
	else:
		team = None
		partner = None
	
	return team, partner, requested_amount

def get_payment_gateway(partner_value):
	"""Get the payment gateway for the partner."""
	partner = frappe.get_doc("Team", partner_value)	
	# Get Mpesa settings for the partner's team
	mpesa_settings = get_mpesa_settings_for_team(partner.name)
	payment_gateway = frappe.get_all("Payment Gateway", filters={"gateway_settings":"Mpesa Settings", "gateway_controller":mpesa_settings.name}, pluck="name")
	if not payment_gateway:
		frappe.throw(_("Payment Gateway not found"), title=_("Mpesa Express Error"))
	gateway=frappe.get_doc("Payment Gateway", payment_gateway[0])
	return gateway.name

def get_mpesa_settings_for_team(team_name):
	"""Fetch Mpesa settings for a given team."""
	
	mpesa_settings = frappe.get_all("Mpesa Settings", filters={"team": team_name}, pluck="name")
	if not mpesa_settings:
		frappe.throw(_("Mpesa Settings not configured for this team"), title=_("Mpesa Express Error"))
	return frappe.get_doc("Mpesa Settings", mpesa_settings[0])

'''ensures number take the right format'''
def sanitize_mobile_number(number):
	"""Add country code and strip leading zeroes from the phone number."""
	return "254" + str(number).lstrip("0")

def validate_mpesa_transaction_currency(currency):
	if currency not in supported_mpesa_currencies:
		frappe.throw(
			_(
				"Please select another payment method. Mpesa does not support transactions in currency '{0}'"
			).format(currency)
		)
  
'''split amount if it exceeds 150,000'''
def split_request_amount_according_to_transaction_limit(amount, transaction_limit):
		request_amount = amount
		if request_amount > transaction_limit:
			# make multiple requests
			request_amounts = []
			requests_to_be_made = frappe.utils.ceil(
				request_amount / transaction_limit
			)  # 480/150 = ceil(3.2) = 4
			for i in range(requests_to_be_made):
				amount = transaction_limit
				if i == requests_to_be_made - 1:
					amount = request_amount - (
						transaction_limit * i
					)  # for 4th request, 480 - (150 * 3) = 30
				request_amounts.append(amount)
		else:
			request_amounts = [request_amount]

		return request_amounts

@frappe.whitelist(allow_guest=True)
def get_exchange_rate(from_currency, to_currency):
	"""Get the latest exchange rate for the given currencies."""
	exchange_rate = frappe.db.get_value(
		"Currency Exchange",
		{"from_currency": from_currency, "to_currency": to_currency},
		"exchange_rate",
		order_by="creation DESC"  
	)
	return exchange_rate


'''fetch parameters from the args'''
def fetch_param_value(response, key, key_field):
	"""Fetch the specified key from list of dictionary. Key is identified via the key field."""
	for param in response:
		if param[key_field] == key:
			return param["Value"]

@frappe.whitelist(allow_guest=True)
def create_exchange_rate(**kwargs):
	"""Create a new exchange rate record."""
	try:
		from_currency = kwargs.get("from_currency", {}).get("value")
		to_currency = kwargs.get("to_currency", {}).get("value")
		exchange_rate = kwargs.get("exchange_rate")
		date = kwargs.get("date")

		if not from_currency or not to_currency or not exchange_rate:
			raise ValueError("Missing required fields.")

		exchange_rate_doc = frappe.get_doc({
			"doctype": "Currency Exchange",
			"from_currency": from_currency,
			"to_currency": to_currency,
			"exchange_rate": exchange_rate,
			"date": date,
		})
		
		exchange_rate_doc.insert(ignore_permissions=True)
		return exchange_rate_doc.name

	except Exception as e:
		print(f"Error: {e}")
		return None

def create_payment_partner_transaction(team, payment_partner, exchange_rate, amount, paid_amount,payment_gateway, payload=None):
			"""Create a Payment Partner Transaction record."""
			transaction_doc = frappe.get_doc({
				"doctype": "Payment Partner Transaction",
				"team": team,
				"payment_partner": payment_partner,
				"exchange_rate": exchange_rate,
				"payment_gateway": payment_gateway,
				"amount": amount,
				"actual_amount": paid_amount,
				"payment_transaction_details": payload
			})
			transaction_doc.insert()
			transaction_doc.submit()
			return transaction_doc.name

@frappe.whitelist(allow_guest=True)
def fetch_currencies():
	"""Fetch the list of currencies supported by the system."""
	currencies = frappe.get_all("Currency", fields=["name"])
	return [currency['name'] for currency in currencies]


@frappe.whitelist(allow_guest=True)
def fetch_payments(payment_gateway, partner, from_date, to_date):
	print("fetching payments", payment_gateway)
	partner = frappe.get_value("Team", {"user": partner}, "name")
	filters = {
		'docstatus': 1,
		'submitted_to_frappe': 0,
		'payment_gateway': payment_gateway,
		'payment_partner':partner
	}

	if from_date and to_date:
		filters['posting_date'] = ['between', [from_date, to_date]]


	partner_payments = frappe.get_all(
		"Payment Partner Transaction",
		filters=filters,
		fields=['name', 'amount', 'posting_date']
	)
	frappe.response.message = partner_payments
	return partner_payments


@frappe.whitelist(allow_guest=True)
def create_payment_partner_payout(from_date, to_date, payment_gateway, payment_partner, payments):
	"""Create a Payment Partner Payout record."""
	partner_commission = frappe.get_value("Team", {"user": payment_partner}, "partner_commission")
	
	# Initialize the main document
	payout_doc = frappe.get_doc({
		"doctype": "Partner Payment Payout",
		"from_date": from_date,
		"to_date": to_date,
		"payment_gateway": payment_gateway,
		"partner": payment_partner,
		"partner_commission": partner_commission,
		"transfer_items": []  # Initialize an empty child table
	})

	# Add each payment to the child table
	for payment in payments:
		payout_doc.append("transfer_items", {
			"transaction_id": payment.get("name"),
			"amount": payment.get("amount"),
			"posting_date": payment.get("posting_date"),
		})
	# Save and submit the document
	payout_doc.insert()
	payout_doc.submit()

	return payout_doc.name

