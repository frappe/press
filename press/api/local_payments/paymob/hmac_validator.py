import hashlib
import hmac
from typing import Any, Dict
from .constants import AcceptCallbackTypes
import frappe


class HMACValidator:
	def __init__(self, incoming_hmac: str, callback_dict: Dict[str, Any], **kwargs) -> None:
		"""Initialize HMAC Attributes

		Args:
			incoming_hmac (str): Incoming Paymob's HMAC
			callback_dict Dict[str, Any]: Incoming Callback Dict
		"""
		self.incoming_hmac = incoming_hmac
		self.callback_dict = callback_dict
		if isinstance(self.callback_dict, dict):
			self.callback_obj_dict = self.callback_dict.get("obj")

		super().__init__(**kwargs)

	@staticmethod
	def _calculate_hmac(message: str) -> str:
		"""Calculates HMAC

		Args:
			message (str): GeneratedHMAC Message

		Returns:
			str: Calculated HMAC
		"""
		hmac_secret = frappe.get_doc("Paymob Settings").get_password("hmac").encode("utf-8")
		return (
			hmac.new(
				hmac_secret,
				message.encode("utf-8"),
				hashlib.sha512,
			)
			.hexdigest()
			.lower()
		)

	@classmethod
	def _generate_processed_hmac(cls, hmac_dict: Dict[str, Any]) -> str:
		"""Creates HMAC from sent self.callback_obj_dict

		Args:
			hmac_dict (Dict[str, Any]): Hmac Dict

		Returns:
			str: Generated HMAC
		"""
		if not isinstance(hmac_dict, dict):
			return ""

		message = ""
		for value in hmac_dict.values():
			if isinstance(value, bool):
				value = str(value).lower()
			if value is None:
				value = ""
			message += str(value)

		return cls._calculate_hmac(message=message)

	def _generate_transaction_processed_hmac(self) -> str:
		"""Creates HMAC from sent transaction callback self.callback_obj_dict

		Returns:
			str: Generated HMAC
		"""
		if not isinstance(self.callback_obj_dict, dict):
			return ""

		hmac_dict = {
			"amount_cents": self.callback_obj_dict.get("amount_cents"),
			"created_at": self.callback_obj_dict.get("created_at"),
			"currency": self.callback_obj_dict.get("currency"),
			"error_occured": self.callback_obj_dict.get("error_occured"),
			"has_parent_transaction": self.callback_obj_dict.get("has_parent_transaction"),
			"id": self.callback_obj_dict.get("id"),
			"integration_id": self.callback_obj_dict.get("integration_id"),
			"is_3d_secure": self.callback_obj_dict.get("is_3d_secure"),
			"is_auth": self.callback_obj_dict.get("is_auth"),
			"is_capture": self.callback_obj_dict.get("is_capture"),
			"is_refunded": self.callback_obj_dict.get("is_refunded"),
			"is_standalone_payment": self.callback_obj_dict.get("is_standalone_payment"),
			"is_voided": self.callback_obj_dict.get("is_voided"),
			"order.id": self.callback_obj_dict.get("order", {}).get("id"),
			"owner": self.callback_obj_dict.get("owner"),
			"pending": self.callback_obj_dict.get("pending"),
			"source_data.pan": self.callback_obj_dict.get("source_data", {}).get("pan"),
			"source_data.sub_type": self.callback_obj_dict.get("source_data", {}).get("sub_type"),
			"source_data.type": self.callback_obj_dict.get("source_data", {}).get("type"),
			"success": self.callback_obj_dict.get("success"),
		}

		return self._generate_processed_hmac(hmac_dict=hmac_dict)

	def _generate_card_token_processed_hmac(self) -> str:
		"""Creates HMAC from sent card token callback body_dic

		Returns:
			str: Generated HMAC
		"""
		if not isinstance(self.callback_obj_dict, dict):
			return ""

		hmac_dict = {
			"card_subtype": self.callback_obj_dict.get("card_subtype"),
			"created_at": self.callback_obj_dict.get("created_at"),
			"email": self.callback_obj_dict.get("email"),
			"id": self.callback_obj_dict.get("id"),
			"masked_pan": self.callback_obj_dict.get("masked_pan"),
			"merchant_id": self.callback_obj_dict.get("merchant_id"),
			"order_id": self.callback_obj_dict.get("order_id"),
			"token": self.callback_obj_dict.get("token"),
		}

		return self._generate_processed_hmac(hmac_dict=hmac_dict)

	def _generate_delivery_status_processed_hmac(self) -> str:
		"""Creates HMAC from sent Delivery Status callback body_dic

		Returns:
			str: Generated HMAC
		"""
		if not isinstance(self.callback_obj_dict, dict):
			return ""

		hmac_dict = {
			"order_id": self.callback_obj_dict.get("order_id"),
			"order_delivery_status": self.callback_obj_dict.get("order_delivery_status"),
			"merchant_id": self.callback_obj_dict.get("merchant_id"),
			"merchant_name": self.callback_obj_dict.get("merchant_name"),
			"updated_at": self.callback_obj_dict.get("updated_at"),
		}

		return self._generate_processed_hmac(hmac_dict=hmac_dict)

	# Public Method that can be used Directly to Validate HMAC
	@property
	def is_valid(self) -> bool:
		"""Validates HMAC for processed callback

		Returns:
			bool: True if HMAC is Valid, False otherwise
		"""
		if not isinstance(self.callback_dict, dict):
			return False

		callback_type = self.callback_dict.get("type")
		if callback_type == AcceptCallbackTypes.TRANSACTION:
			calculated_hmac = self._generate_transaction_processed_hmac()
		elif callback_type == AcceptCallbackTypes.CARD_TOKEN:
			calculated_hmac = self._generate_card_token_processed_hmac()
		elif callback_type == AcceptCallbackTypes.DELIVERY_STATUS:
			calculated_hmac = self._generate_delivery_status_processed_hmac()
		else:
			return False

		if calculated_hmac != self.incoming_hmac:
			return False

		return True
