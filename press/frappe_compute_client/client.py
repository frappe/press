from frappe.frappeclient import FrappeClient


class Client:
	def __init__(self, url, api_key: str, api_secret: str):
		self.client = FrappeClient(url, api_key=api_key, api_secret=api_secret)

	def validate(self):
		return self.client.get_api("frappe.auth.get_logged_user") == "Administrator"
