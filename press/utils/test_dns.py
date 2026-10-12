# Copyright (c) 2026, Frappe and Contributors
# See license.txt

from unittest.mock import Mock, patch

from frappe.tests.utils import FrappeTestCase

from press.utils.dns import _change_dns_record


def route53_client():
	client = Mock()
	client.list_hosted_zones_by_name.return_value = {
		"HostedZones": [{"Name": "fc.dev.", "Id": "/hostedzone/ZONE"}]
	}
	return client


def root_domain():
	domain = Mock(generic_dns_provider=False, aws_region="ap-south-1")
	domain.name = "fc.dev"  # Mock(name=...) names the mock, it doesn't set the attribute
	return domain


def sent_ttl(client):
	change = client.change_resource_record_sets.call_args.kwargs["ChangeBatch"]["Changes"][0]
	return change["ResourceRecordSet"]["TTL"]


class TestChangeDNSRecord(FrappeTestCase):
	def test_dns_record_change_uses_default_ttl_of_600(self):
		client = route53_client()
		with patch("press.utils.dns.boto3.client", return_value=client):
			_change_dns_record("UPSERT", root_domain(), "n2.fc.dev", record_name="site.fc.dev")
		self.assertEqual(sent_ttl(client), 600)

	def test_dns_record_delete_sends_the_given_ttl_so_route53_matches_older_records(self):
		client = route53_client()
		with patch("press.utils.dns.boto3.client", return_value=client):
			_change_dns_record("DELETE", root_domain(), "n1.fc.dev", record_name="site.fc.dev", ttl=900)
		self.assertEqual(sent_ttl(client), 900)
