import requests
from .paymob_urls import PaymobUrls
import json
import frappe

class AcceptAPI:
	def __init__(self):
		self.paymob_settings = frappe.get_doc("Paymob Settings")
		self.paymob_urls = PaymobUrls()

	def retrieve_auth_token(self):
		"""
		Authentication Request:
		:return: token: Authentication token, which is valid for one hour from the creation time.
		"""
		data = {'api_key': self.paymob_settings.get_password("api_key")}
		r = requests.post(self.paymob_urls.get_url("auth") , json=data)
		token = r.json().get('token')
		frappe.db.set_value("Paymob Settings", "Paymob Settings", "token", token)
		frappe.db.commit()
		return token

	def order_registration(self, data):
		"""
		Order Registration API
		:param data: Order data
		:return: registered order
		"""
		r = requests.post(self.paymob_urls.get_url("order"), json=data)
		order = r.json()
		return order

	def payment_key_request(self, data):
		r = requests.post(self.paymob_urls.get_url("payment_key"), json=data)
		payment_token = r.json().get('token')
		return payment_token

	def pay(self, identifier, payment_method, payment_token):
		data = {
			"source": {
				"identifier": identifier,
				"subtype": payment_method
			},
			"payment_token": payment_token
		}
		r = requests.post(self.paymob_urls.get_url("payment"), json=data)
		transaction = r.json()
		return transaction

	def capture_transaction(self, transaction_id, amount_cents):
		auth_token = self.retrieve_auth_token()
		data = {
			"auth_token": auth_token,
			"transaction_id": transaction_id,
			"amount_cents": amount_cents
		}
		r = requests.post(self.paymob_urls.get_url("capture"), json=data)

		transaction = r.json()
		return transaction

	def refund_transaction(self, transaction_id, amount_cents):
		auth_token = self.retrieve_auth_token()
		data = {
			"auth_token": auth_token,
			"transaction_id": transaction_id,
			"amount_cents": amount_cents
		}
		r = requests.post(self.paymob_urls.get_url("refund"), json=data)

		transaction = r.json()
		return transaction

	def void_transaction(self, transaction_id):
		auth_token = self.retrieve_auth_token()
		data = {
			"transaction_id": transaction_id,
		}
		r = requests.post(self.paymob_urls.get_url("void").format(token=str(auth_token)), json=data)

		transaction = r.json()
		return transaction

	def retrieve_transaction(self, transaction_id):
		auth_token = self.retrieve_auth_token()
		r = requests.get(self.paymob_urls.get_url("retrieve_transaction", id=transaction_id, token=auth_token))
		transaction = r.json()
		
		return transaction
	
	# retrieve_transactions
	def retrieve_transactions(self, page=1, page_size=50):
		auth_token = self.retrieve_auth_token()
		r = requests.get(self.paymob_urls.get_url("retrieve_transactions", from_page=page, page_size=page_size, token=auth_token))
		transactions = r.json()
		
		return transactions


	def inquire_transaction(self, merchant_order_id, order_id):
		auth_token = self.retrieve_auth_token()
		payload = {
			"auth_token": auth_token,
			"merchant_order_id": merchant_order_id,
			"order_id": order_id
		}

		r = requests.post(self.paymob_urls.get_url("inquire_transaction"), json=payload)

		transaction = r.json()
		return transaction

	def tracking(self, order_id):
		auth_token = self.retrieve_auth_token()
		r = requests.get(self.paymob_urls.get_url("tracking", order_id=order_id, token=auth_token))
		order = r.json()
		return order

	def preparing_package(self, order_id):
		auth_token = self.retrieve_auth_token()
		pdf_link = self.paymob_urls.get_url("preparing_package", order_id=order_id, token=auth_token)
		return pdf_link

	def loyalty_checkout(self, transaction_reference, otp, payment_token):
		data = {
			"reference": transaction_reference,
			"otp": otp,
			"payment_token": payment_token
		}

		r = requests.post(self.paymob_urls.get_url("loyalty_checkout"), json=data)
		response = r.json()
		return response

	def retrieve_iframe(self, iframe_id, payment_token):
		iframe_url = self.paymob_urls.get_url("iframe", iframe_id=self.paymob_settings.iframe, payment_token=payment_token)
		return iframe_url
	
	def create_payment_intent(self, data):
		"""
		Creates a Paymob Payment Intent
		:param data: Dictionary containing payment intent details (refer to Paymob documentation)
		:return: response object from the Paymob API
		"""

		url = "https://accept.paymob.com/v1/intention/" 
		headers = {
			'Authorization': f'Token {self.paymob_settings.get_password("secret_key")}',
			'Content-Type': 'application/json'
		}

		payload = json.dumps(data)

		try:
			response = requests.request("POST", url, headers=headers, data=payload)
			return response.json()
		except requests.exceptions.RequestException as e:
			print(f"Error creating payment intent: {e}")
		return None

