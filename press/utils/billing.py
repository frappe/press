import frappe
import stripe
from frappe.utils import fmt_money
from press.utils import get_current_team
from press.exceptions import CentralServerNotSet, FrappeioServerNotSet


states_with_tin = {
	"Andaman and Nicobar Islands": "35",
	"Andhra Pradesh": "37",
	"Arunachal Pradesh": "12",
	"Assam": "18",
	"Bihar": "10",
	"Chandigarh": "04",
	"Chattisgarh": "22",
	"Dadra and Nagar Haveli": "26",
	"Daman and Diu": "25",
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
	"Pondicherry": "34",
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


def format_stripe_money(amount, currency):
	return fmt_money(amount / 100, 2, currency)


def get_erpnext_com_connection():
	from frappe.frappeclient import FrappeClient

	# TODO: Remove password authentication when API Key Authentication bug is fixed
	press_settings = frappe.get_single("Press Settings")
	erpnext_password = frappe.utils.password.get_decrypted_password(
		"Press Settings", "Press Settings", fieldname="erpnext_password"
	)
	if not (
		press_settings.erpnext_username and press_settings.erpnext_url and erpnext_password
	):
		frappe.throw("ERPNext.com URL not set up in Press Settings", exc=CentralServerNotSet)

	return FrappeClient(
		press_settings.erpnext_url,
		username=press_settings.erpnext_username,
		password=erpnext_password,
	)


def get_frappe_io_connection():
	if hasattr(frappe.local, "press_frappeio_conn"):
		return frappe.local.press_frappeio_conn

	from frappe.frappeclient import FrappeClient

	press_settings = frappe.get_single("Press Settings")
	frappe_password = press_settings.get_password("frappe_password", raise_exception=False)
	if not (frappe_password and press_settings.frappe_url):
		frappe.throw("Frappe.io URL not set up in Press Settings", exc=FrappeioServerNotSet)

	frappe.local.press_frappeio_conn = FrappeClient(
		press_settings.frappe_url,
		username=press_settings.frappe_username,
		password=frappe_password,
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
	strip_account = frappe.db.get_single_value("Press Settings", "stripe_account")
	return frappe.db.get_value("Stripe Settings", strip_account, "publishable_key")


def get_setup_intent(team):
	intent = frappe.cache().hget("setup_intent", team)
	if not intent:
		customer_id = frappe.db.get_value("Team", team, "stripe_customer_id")
		stripe = get_stripe()
		intent = stripe.SetupIntent.create(
			customer=customer_id, payment_method_types=["card"]
		)
		frappe.cache().hset("setup_intent", team, intent)
	return intent


def get_stripe():
	if not hasattr(frappe.local, "press_stripe_object"):
		stripe_account = frappe.db.get_single_value("Press Settings", "stripe_account")
		secret_key = frappe.utils.password.get_decrypted_password(
			"Stripe Settings", stripe_account, "secret_key", raise_exception=False
		)

		if not (stripe_account and secret_key):
			frappe.throw(
				"Setup stripe via Press Settings before using press.api.billing.get_stripe"
			)

		stripe.api_key = secret_key
		frappe.local.press_stripe_object = stripe

	return frappe.local.press_stripe_object
