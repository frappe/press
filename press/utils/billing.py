import re

import frappe
import razorpay
import stripe
from frappe.utils import fmt_money

from press.exceptions import CentralServerNotSet, FrappeioServerNotSet
from press.utils import get_current_team, log_error
from frappe.utils import get_request_site_address
from press.press.doctype.mpesa_settings.mpesa_connector import MpesaConnector
from json import dumps, loads
from frappe.integrations.utils import create_request_log

states_with_tin = {
	"Andaman and Nicobar Islands": "35",
	"Andhra Pradesh": "37",
	"Arunachal Pradesh": "12",
	"Assam": "18",
	"Bihar": "10",
	"Chandigarh": "04",
	"Chhattisgarh": "22",
	"Dadra and Nagar Haveli and Daman and Diu": "26",
	"Delhi": "07",
	"Goa": "30",
	"Gujarat": "24",
	"Haryana": "06",
	"Himachal Pradesh": "02",
	"Jammu and Kashmir": "01",
	"Jharkhand": "20",
	"Karnataka": "29",
	"Kerala": "32",
	"Ladakh": "38",
	"Lakshadweep Islands": "31",
	"Madhya Pradesh": "23",
	"Maharashtra": "27",
	"Manipur": "14",
	"Meghalaya": "17",
	"Mizoram": "15",
	"Nagaland": "13",
	"Odisha": "21",
	"Other Territory": "97",
	"Puducherry": "34",
	"Punjab": "03",
	"Rajasthan": "08",
	"Sikkim": "11",
	"Tamil Nadu": "33",
	"Telangana": "36",
	"Tripura": "16",
	"Uttar Pradesh": "09",
	"Uttarakhand": "05",
	"West Bengal": "19",
}

GSTIN_FORMAT = re.compile(
	"^[0-9]{2}[A-Z]{4}[0-9A-Z]{1}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}[1-9A-Z]{1}[0-9A-Z]{1}$"
)
supported_mpesa_currencies = ["KES"]


def format_stripe_money(amount, currency):
	return fmt_money(amount / 100, 2, currency)


def get_erpnext_com_connection():
	from frappe.frappeclient import FrappeClient

	press_settings = frappe.get_single("Press Settings")
	erpnext_api_secret = press_settings.get_password(
		"erpnext_api_secret", raise_exception=False
	)

	if not (
		press_settings.erpnext_api_key and press_settings.erpnext_url and erpnext_api_secret
	):
		frappe.throw("ERPNext.com URL not set up in Press Settings", exc=CentralServerNotSet)

	return FrappeClient(
		press_settings.erpnext_url,
		api_key=press_settings.erpnext_api_key,
		api_secret=erpnext_api_secret,
	)


def get_frappe_io_connection():
	if hasattr(frappe.local, "press_frappeio_conn"):
		return frappe.local.press_frappeio_conn

	from frappe.frappeclient import FrappeClient

	press_settings = frappe.get_single("Press Settings")
	frappe_api_key = press_settings.frappeio_api_key
	frappe_api_secret = press_settings.get_password(
		"frappeio_api_secret", raise_exception=False
	)

	if not (frappe_api_key and frappe_api_secret and press_settings.frappe_url):
		frappe.throw("Frappe.io URL not set up in Press Settings", exc=FrappeioServerNotSet)

	frappe.local.press_frappeio_conn = FrappeClient(
		press_settings.frappe_url, api_key=frappe_api_key, api_secret=frappe_api_secret
	)

	return get_frappe_io_connection()


def make_formatted_doc(doc, fieldtypes=None):
	formatted = {}
	filters = None
	if fieldtypes:
		filters = {"fieldtype": ["in", fieldtypes]}

	for df in doc.meta.get("fields", filters):
		formatted[df.fieldname] = doc.get_formatted(df.fieldname)

	for tf in doc.meta.get_table_fields():
		formatted[tf.fieldname] = []
		for row in doc.get(tf.fieldname):
			formatted[tf.fieldname].append(make_formatted_doc(row))

	return formatted


def clear_setup_intent():
	team = get_current_team()
	frappe.cache().hdel("setup_intent", team)


def get_publishable_key():
	return frappe.db.get_single_value("Press Settings", "stripe_publishable_key")


def get_setup_intent(team):
	from frappe.utils import random_string

	intent = frappe.cache().hget("setup_intent", team)
	if not intent:
		data = frappe.db.get_value("Team", team, ["stripe_customer_id", "currency"])
		customer_id = data[0]
		currency = data[1]
		stripe = get_stripe()
		hash = random_string(10)
		intent = stripe.SetupIntent.create(
			customer=customer_id,
			payment_method_types=["card"],
			payment_method_options={
				"card": {
					"request_three_d_secure": "automatic",
					"mandate_options": {
						"reference": f"Mandate-team:{team}-{hash}",
						"amount_type": "maximum",
						"amount": 1500000,
						"currency": currency.lower(),
						"start_date": int(frappe.utils.get_timestamp()),
						"interval": "sporadic",
						"supported_types": ["india"],
					},
				}
			},
		)
		frappe.cache().hset("setup_intent", team, intent)

	return intent


def get_stripe():
	from frappe.utils.password import get_decrypted_password

	if not hasattr(frappe.local, "press_stripe_object"):
		secret_key = get_decrypted_password(
			"Press Settings",
			"Press Settings",
			"stripe_secret_key",
			raise_exception=False,
		)

		if not secret_key:
			frappe.throw(
				"Setup stripe via Press Settings before using press.api.billing.get_stripe"
			)

		stripe.api_key = secret_key
		frappe.local.press_stripe_object = stripe

	return frappe.local.press_stripe_object


def convert_stripe_money(amount):
	return (amount / 100) if amount else 0


def validate_gstin_check_digit(gstin, label="GSTIN"):
	"""Function to validate the check digit of the GSTIN."""
	factor = 1
	total = 0
	code_point_chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
	mod = len(code_point_chars)
	input_chars = gstin[:-1]
	for char in input_chars:
		digit = factor * code_point_chars.find(char)
		digit = (digit // mod) + (digit % mod)
		total += digit
		factor = 2 if factor == 1 else 1
	if gstin[-1] != code_point_chars[((mod - (total % mod)) % mod)]:
		frappe.throw(
			"""Invalid {0}! The check digit validation has failed. Please ensure you've typed the {0} correctly.""".format(
				label
			)
		)


def get_razorpay_client():
	from frappe.utils.password import get_decrypted_password

	if not hasattr(frappe.local, "press_razorpay_client_object"):
		key_id = frappe.db.get_single_value("Press Settings", "razorpay_key_id")
		key_secret = get_decrypted_password(
			"Press Settings", "Press Settings", "razorpay_key_secret", raise_exception=False
		)

		if not (key_id and key_secret):
			frappe.throw(
				"Setup razorpay via Press Settings before using"
				" press.api.billing.get_razorpay_client"
			)

		frappe.local.press_razorpay_client_object = razorpay.Client(auth=(key_id, key_secret))

	return frappe.local.press_razorpay_client_object


def process_micro_debit_test_charge(stripe_event):
	try:
		payment_intent = stripe_event["data"]["object"]
		metadata = payment_intent.get("metadata")
		payment_method_name = metadata.get("payment_method_name")

		frappe.db.set_value(
			"Stripe Payment Method", payment_method_name, "is_verified_with_micro_charge", True
		)

		frappe.get_doc(
			doctype="Stripe Micro Charge Record",
			stripe_payment_method=payment_method_name,
			stripe_payment_intent_id=payment_intent.get("id"),
		).insert(ignore_permissions=True)
	except Exception:
		log_error("Error Processing Stripe Micro Debit Charge", body=stripe_event)


#Mpesa integrations, mpesa express
def validate_mpesa_transaction_currency(currency):
	if currency not in supported_mpesa_currencies:
		frappe.throw(
			_(
				"Please select another payment method. Mpesa does not support transactions in currency '{0}'"
			).format(currency)
		)
'''ensures number take the right format'''
def sanitize_mobile_number(number):
	"""Add country code and strip leading zeroes from the phone number."""
	return "254" + str(number).lstrip("0")


'''splitas amount if it exceeds 150,000'''
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

'''Send stk push to the user'''
def generate_stk_push(**kwargs):
	"""Generate stk push by making a API call to the stk push API."""
	args = frappe._dict(kwargs)
	try:
		callback_url = (
			get_request_site_address(True)
			+ "/api/method/press.press.doctype.mpesa_settings.mpesa_settings.verify_transaction"
		)

		mpesa_settings = frappe.get_doc("Mpesa Settings", args.payment_gateway[6:])
		env = "production" if not mpesa_settings.sandbox else "sandbox"
		# for sandbox, business shortcode is same as till number
		business_shortcode = (
			mpesa_settings.business_shortcode if env == "production" else mpesa_settings.till_number
		)

		connector = MpesaConnector(
			env=env,
			app_key=mpesa_settings.consumer_key,
			app_secret=mpesa_settings.get_password("consumer_secret"),
		)

		mobile_number = sanitize_mobile_number(args.sender)

		response = connector.stk_push(
			business_shortcode=business_shortcode,
			amount=args.request_amount,
			passcode=mpesa_settings.get_password("online_passkey"),
			callback_url=callback_url,
			reference_code=mpesa_settings.till_number,
			phone_number=mobile_number,
			description="Frappe Cloud Payment",
		)

		return response

	except Exception:
		frappe.log_error("Mpesa Express Transaction Error")
		frappe.throw(
			_("Issue detected with Mpesa configuration, check the error logs for more details"),
			title=_("Mpesa Express Error"),
		)
  

'''Verify transaction after push notification'''
@frappe.whitelist(allow_guest=True)
def verify_pesa_transaction(**kwargs):
	"""Verify the transaction result received via callback from STK."""
	transaction_response = frappe._dict(kwargs["Body"]["stkCallback"])

	checkout_id = getattr(transaction_response, "CheckoutRequestID", "")
	if not isinstance(checkout_id, str):
		frappe.throw(_("Invalid Checkout Request ID"))

	# Retrieve the corresponding Integration Request document
	integration_request = frappe.get_doc("Integration Request", checkout_id)
	transaction_data = frappe._dict(loads(integration_request.data))
	total_paid = 0  
	success = False

	if transaction_response["ResultCode"] == 0:  # Transaction was successful
		if integration_request.reference_doctype and integration_request.reference_docname:
			try:
				item_response = transaction_response["CallbackMetadata"]["Item"]
				amount = fetch_param_value(item_response, "Amount", "Name")
				mpesa_receipt = fetch_param_value(item_response, "MpesaReceiptNumber", "Name")
				
				# Fetch the document associated with the payment
				pr = frappe.get_doc(
					integration_request.reference_doctype, integration_request.reference_docname
				)

				# Get completed payments and receipts for the integration request
				mpesa_receipts, completed_payments = get_completed_integration_requests_info(
					integration_request.reference_doctype, integration_request.reference_docname, checkout_id
				)

				total_paid = amount + sum(completed_payments)
				mpesa_receipts = ", ".join(mpesa_receipts + [mpesa_receipt])

				# if total_paid >= pr.grand_total:
				pr.run_method("on_payment_authorized", "Completed")
				success = True

				# Mark the Integration Request as successful
				integration_request.handle_success(transaction_response)
			except Exception:
				# Handle failure scenario and log an error
				integration_request.handle_failure(transaction_response)
				frappe.log_error("Mpesa: Failed to verify transaction")

	else:
		# If the transaction was not successful, handle the failure
		integration_request.handle_failure(transaction_response)
 
 
'''fetch parameters from the args'''
def fetch_param_value(response, key, key_field):
	"""Fetch the specified key from list of dictionary. Key is identified via the key field."""
	for param in response:
		if param[key_field] == key:
			return param["Value"]

'''get completed integration requests'''
def get_completed_integration_requests_info(reference_doctype, reference_docname, checkout_id):
	output_of_other_completed_requests = frappe.get_all(
		"Integration Request",
		filters={
			"name": ["!=", checkout_id],
			"reference_doctype": reference_doctype,
			"reference_docname": reference_docname,
			"status": "Completed",
		},
		pluck="output",
	)

	mpesa_receipts, completed_payments = [], []

	for out in output_of_other_completed_requests:
		out = frappe._dict(loads(out))
		item_response = out["CallbackMetadata"]["Item"]
		completed_amount = fetch_param_value(item_response, "Amount", "Name")
		completed_mpesa_receipt = fetch_param_value(item_response, "MpesaReceiptNumber", "Name")
		completed_payments.append(completed_amount)
		mpesa_receipts.append(completed_mpesa_receipt)

	return mpesa_receipts, completed_payments

'''request for payments'''
def request_for_payment(**kwargs):
		args = frappe._dict(kwargs)
		request_amounts = split_request_amount_according_to_transaction_limit(args.request_amount)

		for i, amount in enumerate(request_amounts):
			args.request_amount = amount
			if frappe.flags.in_test:
				from press.press.doctype.mpesa_settings.test_mpesa_settings import (
					get_payment_request_response_payload,
				)

				response = frappe._dict(get_payment_request_response_payload(amount))
			else:
				response = frappe._dict(generate_stk_push(**args))

			handle_api_response("CheckoutRequestID", args, response)
   
   
def handle_api_response(global_id, request_dict, response):
		"""Response received from API calls returns a global identifier for each transaction, this code is returned during the callback."""
		# check error response
		if getattr(response, "requestId"):
			req_name = getattr(response, "requestId")
			error = response
		else:
			# global checkout id used as request name
			req_name = getattr(response, global_id)
			error = None

		if not frappe.db.exists("Integration Request", req_name):
			create_request_log(request_dict, "Host", "Mpesa", req_name, error)

		if error:
			frappe.throw(_(getattr(response, "errorMessage")), title=_("Transaction Error"))