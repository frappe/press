from frappe.tests.utils import FrappeTestCase

from press.incident_management.support_agent.redaction import redact, redact_text


class TestSupportAgentRedaction(FrappeTestCase):
	def test_redacts_common_personal_and_secret_values(self):
		text = "email a@example.com token=abc123 Authorization: Bearer secret 10.0.0.1"

		redacted = redact_text(text)

		self.assertNotIn("a@example.com", redacted)
		self.assertNotIn("abc123", redacted)
		self.assertNotIn("secret", redacted)
		self.assertNotIn("10.0.0.1", redacted)

	def test_redacts_secret_dict_keys_recursively(self):
		payload = {"site": "test.frappe.cloud", "nested": {"password": "admin"}}

		self.assertEqual(redact(payload)["nested"]["password"], "[REDACTED]")
