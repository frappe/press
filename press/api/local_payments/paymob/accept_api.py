from typing import Any, Dict, List, Tuple, Union
import frappe
import requests
import json

from .paymob_urls import PaymobUrls
from .connection import AcceptConnection

from .data_classes.response_feedback_dataclass import ResponseFeedBack
from .response_codes import SUCCESS


class AcceptAPI:
	def __init__(self) -> None:
		"""Class for Accept APIs
		By Initializing an Instance from This class, an auth token is obtained automatically
		and You will be able to call The Following APIs:
		- Create Payment Intention
		- Get Transaction Details
		"""
		self.connection = AcceptConnection()
		self.paymob_settings = frappe.get_doc("Paymob Settings")
		self.paymob_urls = PaymobUrls()

	def retrieve_auth_token(self):
		"""
		Authentication Request:
		:return: token: Authentication token, which is valid for one hour from the creation time.
		"""
		return self.connection.auth_token

	def create_payment_intent(
		self, data: Dict
	) -> Tuple[str, Union[Dict, None], ResponseFeedBack]:
		"""
		Creates a Paymob Payment Intent
		:param data: Dictionary containing payment intent details (refer to Paymob documentation)
		:return: Tuple[str, Union[Dict, None], ResponseFeedBack]: (Code, Dict, ResponseFeedBack Instance)

		"""

		headers = {
			"Authorization": f"Token {self.paymob_settings.get_password('secret_key')}",
			"Content-Type": "application/json",
		}
		payload = json.dumps(data)
		code, feedback = self.connection.post(
			url=self.paymob_urls.get_url("intention"), headers=headers, data=payload
		)

		payment_intent = frappe._dict()

		if code == SUCCESS:
			payment_intent = feedback.data
			feedback.message = "Payment Intention Created Successfully"

		return code, payment_intent, feedback

	def retrieve_transaction(
		self, transaction_id: int
	) -> Tuple[str, Union[Dict, None], ResponseFeedBack]:
		"""Retrieves Transaction Data by Transaction ID

		Args:
			transaction_id (int): Paymob's Transaction ID

		Returns:
			Tuple[str, Union[Dict, None], ResponseFeedBack]: (Code, Dict, ResponseFeedBack Instance)
		"""
		code, feedback = self.connection.get(
			url=self.paymob_urls.get_url("retrieve_transaction", id=transaction_id)
		)
		transaction = None
		if code == SUCCESS:
			transaction = feedback.data
			feedback.message = (
				f"Transaction with id {transaction_id} retrieved Scuccessfully"
			)
		return code, transaction, feedback

	def retrieve_iframe(self, iframe_id, payment_token):
		iframe_url = self.paymob_urls.get_url(
			"iframe", iframe_id=self.paymob_settings.iframe, payment_token=payment_token
		)
		return iframe_url
