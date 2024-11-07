import frappe
from press.api.billing import create_balance_transaction
from frappe import _  # Import this for translation functionality

def after_save_mpesa_payment_record(doc, method=None):
	try:
		team = doc.team
		amount = doc.amount_usd
		
		balance_transaction_name = create_balance_transaction(team, amount)
		
		frappe.db.set_value('Mpesa Payment Record', doc.name, 'balance_transaction', balance_transaction_name)
		
		frappe.db.set_value('Mpesa Payment Record', doc.name, 'docstatus', 1)
		doc.reload()
		frappe.db.commit()
		
		frappe.msgprint(_("Mpesa Payment Record has been linked with Balance Transaction and submitted."))
	except Exception as e:
		frappe.throw(_("An error occurred: ") + str(e))
		frappe.log_error(message=str(e), title="Mpesa Payment Submission Failed")
  