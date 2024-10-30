from dataclasses import dataclass
import frappe

@dataclass
class PaymobUrls:
	base_url: str = "https://accept.paymob.com/"

	# Auth
	auth: str = "api/auth/tokens"

	# Ecommerce
	order: str = "api/ecommerce/orders"
	inquire_transaction: str = "api/ecommerce/orders/transaction_inquiry"
	tracking: str = "api/ecommerce/orders/{order_id}/delivery_status?token={token}"
	preparing_package: str = "api/ecommerce/orders/{order_id}/airway_bill?token={token}"

	# Acceptance
	payment_key: str = "api/acceptance/payment_keys"
	payment: str = "api/acceptance/payments/pay"
	capture: str = "api/acceptance/capture"
	refund: str = "api/acceptance/void_refund/refund"
	void: str = "api/acceptance/void_refund/void?token={token}"
	retrieve_transaction: str = "api/acceptance/transactions/{id}"
	retrieve_transactions: str = "api/acceptance/portal-transactions?page={from_page}&page_size={page_size}&token={token}"
	loyalty_checkout: str = "api/acceptance/loyalty_checkout"
	iframe: str = "api/acceptance/iframes/{iframe_id}?payment_token={payment_token}"
	intention: str = "v1/intention/"

	def get_url(self, endpoint, **kwargs):
		# based on available attributes and passed keyword arguments
		return f"{self.base_url}{getattr(self, endpoint)}".format(**kwargs)


# Example usage
# paymob_urls = PaymobUrls()
# order_registration_url = paymob_urls.get_url("order")
# void_transaction_url = paymob_urls.get_url("void", token="your_token")
# tracking_url = paymob_urls.get_url("tracking", order_id="123", token="your_token")
