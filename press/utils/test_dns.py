# Copyright (c) 2026, Frappe and Contributors
# See license.txt

from unittest.mock import Mock, patch

from frappe.tests.utils import FrappeTestCase

from press.utils.dns import _change_dns_record


def route53_client(existing_records=()):
	client = Mock()
	client.list_hosted_zones_by_name.return_value = {
		"HostedZones": [{"Name": "fc.dev.", "Id": "/hostedzone/ZONE"}]
	}
	client.list_resource_record_sets.return_value = {"ResourceRecordSets": list(existing_records)}
	return client


def root_domain():
	domain = Mock(generic_dns_provider=False, aws_region="ap-south-1")
	domain.name = "fc.dev"  # Mock(name=...) names the mock, it doesn't set the attribute
	return domain


def cname(target, ttl):
	return {"Name": "site.fc.dev.", "Type": "CNAME", "TTL": ttl, "ResourceRecords": [{"Value": target}]}


def sent_record(client):
	return client.change_resource_record_sets.call_args.kwargs["ChangeBatch"]["Changes"][0][
		"ResourceRecordSet"
	]


class TestChangeDNSRecord(FrappeTestCase):
	def change(self, client, method, target):
		with patch("press.utils.dns.boto3.client", return_value=client):
			_change_dns_record(method, root_domain(), target, record_name="site.fc.dev")

	def test_dns_record_upsert_sends_ttl_600(self):
		client = route53_client()
		self.change(client, "UPSERT", "n2.fc.dev")
		self.assertEqual(sent_record(client)["TTL"], 600)

	def test_dns_record_delete_sends_the_ttl_route53_has_for_an_older_record(self):
		client = route53_client([cname("n1.fc.dev", 900)])
		self.change(client, "DELETE", "n1.fc.dev")
		self.assertEqual(sent_record(client), cname("n1.fc.dev", 900))

	def test_dns_record_delete_does_not_take_a_record_pointing_at_another_proxy(self):
		client = route53_client([cname("n3.fc.dev", 900)])
		self.change(client, "DELETE", "n1.fc.dev")
		self.assertEqual(sent_record(client)["ResourceRecords"], [{"Value": "n1.fc.dev"}])
		self.assertEqual(sent_record(client)["TTL"], 600)
