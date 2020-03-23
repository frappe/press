import frappe
from press.utils.stripe_controller import StripeController

@frappe.whitelist(allow_guest=True)
def setup_subscription(token):
    print(token)

    sc = StripeController(payer_name='Test', email_id='saurabh6790@gmail.com', token=token)
    sc.set_transaction_currency()
    sc.create_customer()
    sc.create_subscription()
    print(sc.subscription_details)