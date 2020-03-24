import frappe
from press.utils.stripe_controller import StripeController

@frappe.whitelist(allow_guest=True)
def create_customer_and_subscription(email, payment_method):
    sc = StripeController(email_id=email)
    sc.payment_methods = payment_method
    sc.create_customer()

    if sc.customer_obj:
        sc.setup_payment_method()
        sc.create_subscription()

    return {
        "subscription": sc.subscription_details
    }