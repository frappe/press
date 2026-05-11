from frappe.frappeclient import FrappeClient


class FrappePressClient(FrappeClient):
	def post_api(self, method, params=None):
		res = self.session.post(
			f"{self.url}/api/method/{method}", data=params, verify=self.verify, headers=self.headers
		)
		return self.post_process(res)
