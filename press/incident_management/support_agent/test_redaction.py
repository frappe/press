from frappe.tests.utils import FrappeTestCase

from press.incident_management.support_agent.llm import _anonymise
from press.incident_management.support_agent.redaction import redact, redact_text


class TestSupportAgentAnonymisation(FrappeTestCase):
	def test_processlist_keeps_the_target_site_but_drops_other_tenants(self):
		payload = {
			"database_processes": {
				"processes": [
					{"site": "noisy.frappe.cloud", "is_target_site": False},
					{"site": "test.frappe.cloud", "is_target_site": True},
				]
			}
		}

		processes = _anonymise(payload)["database_processes"]["processes"]

		self.assertIsNone(processes[0]["site"])
		self.assertEqual(processes[1]["site"], "test.frappe.cloud")


class TestSupportAgentRedaction(FrappeTestCase):
	def test_redacts_common_personal_and_secret_values(self):
		text = "email a@example.com token=abc123 Authorization: Bearer secret 10.0.0.1"

		redacted = redact_text(text)

		self.assertNotIn("a@example.com", redacted)
		self.assertNotIn("abc123", redacted)
		self.assertNotIn("secret", redacted)
		self.assertNotIn("10.0.0.1", redacted)

	def test_redacts_secret_dict_keys_recursively(self):
		payload = {
			"site": "test.frappe.cloud",
			"nested": {"password": "admin"},  # pragma: allowlist secret
		}

		self.assertEqual(redact(payload)["nested"]["password"], "[REDACTED]")
