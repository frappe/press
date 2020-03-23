import frappe
from press.utils.stripe_controller import StripeController

@frappe.whitelist(allow_guest=True)
def setup_subscription(token):
    print(token)

    sc = StripeController(payer_name='Sau', email_id='palandes06@gmail.com', token=token)
    sc.set_transaction_currency(currency='INR')
    sc.create_customer()
    sc.create_subscription()
    print(sc.subscription_details)