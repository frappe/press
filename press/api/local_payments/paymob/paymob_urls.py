from dataclasses import dataclass
import frappe

@dataclass
class PaymobUrls:
	base_url: str = "https://accept.paymob.com/api/"

	# Auth
	auth: str = "auth/tokens"

	# Ecommerce
	order: str = "ecommerce/orders"
	inquire_transaction: str = "ecommerce/orders/transaction_inquiry"
	tracking: str = "ecommerce/orders/{order_id}/delivery_status?token={token}"
	preparing_package: str = "ecommerce/orders/{order_id}/airway_bill?token={token}"

	# Acceptance
	payment_key: str = "acceptance/payment_keys"
	payment: str = "acceptance/payments/pay"
	capture: str = "acceptance/capture"
	refund: str = "acceptance/void_refund/refund"
	void: str = "acceptance/void_refund/void?token={token}"
	retrieve_transaction: str = "acceptance/transactions/{id}?token={token}"
	retrieve_transactions: str = "acceptance/portal-transactions?page={from_page}&page_size={page_size}&token={token}"
	loyalty_checkout: str = "acceptance/loyalty_checkout"
	iframe: str = "acceptance/iframes/{iframe_id}?payment_token={payment_token}"
	intention: str = "v1/intention"

	def get_url(self, endpoint, **kwargs):
		# based on available attributes and passed keyword arguments
		return f"{self.base_url}{getattr(self, endpoint)}".format(**kwargs)


# Example usage
# paymob_urls = PaymobUrls()
# order_registration_url = paymob_urls.get_url("order")
# void_transaction_url = paymob_urls.get_url("void", token="your_token")
# tracking_url = paymob_urls.get_url("tracking", order_id="123", token="your_token")
