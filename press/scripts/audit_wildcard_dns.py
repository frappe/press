# In bench IPython console:  %run press/scripts/audit_wildcard_dns.py
# Audits the wildcard A record (*.<domain>) of every enabled Root Domain against
# the primary, auto-selectable proxy of its default cluster.
# Prints only the failed domains, then use fix("x.frappe.cloud") to correct one.
import frappe
from dns.resolver import Resolver

from press.utils.dns import NAMESERVERS

resolver = Resolver(configure=False)
resolver.nameservers = NAMESERVERS


def expected_proxy_ip(domain):
	default_cluster = frappe.db.get_value("Root Domain", domain, "default_cluster")
	proxy = frappe.get_all(
		"Proxy Server",
		{
			"cluster": default_cluster,
			"status": "Active",
			"is_primary": 1,
			"exclude_from_auto_selection": 0,
		},
		["name", "ip"],
	)
	if len(proxy) != 1:
		raise Exception(f"expected 1 primary proxy in {default_cluster}, found {[p.name for p in proxy]}")
	return proxy[0].name, proxy[0].ip


def resolved_wildcard(domain):
	return [r.to_text() for r in resolver.query(f"*.{domain}", "A")]


def fix(domain):
	"""UPSERT *.<domain> A record to the default cluster's primary proxy IP."""
	name, ip = expected_proxy_ip(domain)
	doc = frappe.get_doc("Root Domain", domain)
	doc.boto3_client.change_resource_record_sets(
		HostedZoneId=doc.hosted_zone,
		ChangeBatch={
			"Changes": [
				{
					"Action": "UPSERT",
					"ResourceRecordSet": {
						"Name": f"*.{domain}",
						"Type": "A",
						"TTL": 600,
						"ResourceRecords": [{"Value": ip}],
					},
				}
			]
		},
	)
	print(f"UPDATED {domain}: *.{domain} -> {ip} ({name})")


failed = []
for domain in frappe.get_all("Root Domain", {"enabled": 1}, pluck="name"):
	try:
		_, ip = expected_proxy_ip(domain)
		if resolved_wildcard(domain) != [ip]:
			failed.append(domain)
	except Exception as e:
		print(f"# {domain}: {e}")
		failed.append(domain)

print("\nFailed root domains:")
for domain in failed:
	print(f"  fix({domain!r})")
