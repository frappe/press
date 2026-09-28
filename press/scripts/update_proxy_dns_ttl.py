# In bench IPython console:  %run press/scripts/update_proxy_dns_ttl.py
# Sets the TTL of the A record of every proxy server to NEW_TTL.
# Prints the changes only. Set DRY_RUN = False to write them.
import frappe

from press.press.doctype.root_domain.root_domain import RootDomain

DRY_RUN = True
NEW_TTL = 3600

# Failover lowers the TTL to 60 on purpose, so skip proxies in an unfinished failover
failing_over: set[str] = set()
for failover in frappe.get_all(
	"Proxy Failover", {"status": ("in", ["Pending", "Running"])}, ["primary", "secondary"]
):
	failing_over.update((failover.primary, failover.secondary))

# No functions or comprehensions: pasted into bench console, they can't see top-level names
for proxy in frappe.get_all("Proxy Server", {"status": ("!=", "Archived")}, ["name", "domain"]):
	if proxy.name in failing_over:
		print(proxy.name, "SKIPPED: failover in progress")
		continue
	domain = RootDomain("Root Domain", proxy.domain)
	try:
		zone = domain.hosted_zone
	except TypeError:
		print(proxy.name, "SKIPPED: no hosted zone for", proxy.domain)
		continue
	response = domain.boto3_client.list_resource_record_sets(
		HostedZoneId=zone, StartRecordName=proxy.name, StartRecordType="A", MaxItems="1"
	)
	records = response["ResourceRecordSets"]
	if not records or records[0]["Name"] != f"{proxy.name}." or records[0]["Type"] != "A":
		print(proxy.name, "MISSING: no A record")
		continue
	record = records[0]
	if record.get("TTL") in (None, NEW_TTL):
		continue
	print(proxy.name, record["ResourceRecords"], record["TTL"], "->", NEW_TTL)
	record["TTL"] = NEW_TTL
	if not DRY_RUN:
		print(
			domain.boto3_client.change_resource_record_sets(
				HostedZoneId=zone,
				ChangeBatch={"Changes": [{"Action": "UPSERT", "ResourceRecordSet": record}]},
			)
		)
