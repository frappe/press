from press.api.billing import get_current_team
import frappe

@frappe.whitelist(allow_guest=True)
def create_mpesa_settings(**kwargs):
	"""Create Mpesa Settings for the team."""
	team = get_current_team()

	try:
		mpesa_settings = frappe.get_doc({
			"doctype": "Mpesa Settings",
			"team": team,  
			"payment_gateway_name": kwargs.get("payment_gateway_name"),
			"api_type": "Mpesa Express",
			"consumer_key": kwargs.get("consumer_key"),  
			"consumer_secret": kwargs.get("consumer_secret"),  
			"business_shortcode": kwargs.get("short_code"),  
			"till_number": kwargs.get("till_number"), 
			"online_passkey": kwargs.get("pass_key"), 
			"security_credential": kwargs.get("security_credential"),
			"sandbox": 1 if kwargs.get("sandbox") else 0,
		})

		mpesa_settings.insert(ignore_permissions=True)
		frappe.db.commit()

		return mpesa_settings.name 
	except Exception as e:
		frappe.log_error(message=f"Error creating Mpesa Settings: {str(e)}", title="M-Pesa Settings Creation Error")
		return None  
