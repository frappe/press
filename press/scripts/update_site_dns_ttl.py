# In bench IPython console:  %run press/scripts/update_site_dns_ttl.py
# Sets the TTL of every site CNAME record (pointing to a proxy or a standalone server) to NEW_TTL.
# Prints counts only. Set DRY_RUN = False to write the changes.
from collections import Counter

import frappe

from press.press.doctype.root_domain.root_domain import RootDomain

DRY_RUN = True
NEW_TTL = 900

proxies = set(frappe.get_all("Proxy Server", pluck="name"))
targets = set(proxies)
targets.update(frappe.get_all("Server", {"is_standalone": 1}, pluck="name"))

# No functions or comprehensions: pasted into bench console, they can't see top-level names
for name in frappe.get_all("Root Domain", {"dns_provider": "AWS Route 53"}, pluck="name"):
	# Ask before the read, so that no records go stale while the prompt waits
	if input(f"{name}: update? [y/N] ") != "y":
		continue
	domain = RootDomain("Root Domain", name)
	try:
		zone = domain.hosted_zone
	except TypeError:
		print(name, "SKIPPED: no hosted zone")
		continue
	counts_by_old_ttl: Counter = Counter()
	paginator = domain.boto3_client.get_paginator("list_resource_record_sets")
	for page in paginator.paginate(HostedZoneId=zone):
		changes = []
		for record in page["ResourceRecordSets"]:
			if record["Type"] != "CNAME" or record.get("TTL") in (None, NEW_TTL):
				continue
			if not record["Name"].endswith(f".{name}."):
				continue
			if record["Name"].rstrip(".") in proxies:
				print(record["Name"], "SKIPPED: proxy server")
				continue
			value = record["ResourceRecords"][0]["Value"].rstrip(".")
			if value not in targets:
				continue
			counts_by_old_ttl[record["TTL"]] += 1
			record["TTL"] = NEW_TTL
			changes.append({"Action": "UPSERT", "ResourceRecordSet": record})
		if changes and not DRY_RUN:
			domain.boto3_client.change_resource_record_sets(
				HostedZoneId=zone, ChangeBatch={"Changes": changes}
			)
	print(name, "old TTLs:", dict(counts_by_old_ttl))
