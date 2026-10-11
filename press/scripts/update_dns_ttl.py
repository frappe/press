# In bench IPython console:  %run press/scripts/update_dns_ttl.py
# Raises the TTL of every OLD_TTL CNAME and A record under each Route 53 Root Domain.
# Prints the changes only. Set DRY_RUN = False to write them.
import frappe

from press.press.doctype.root_domain.root_domain import RootDomain

DRY_RUN = True
OLD_TTL, NEW_TTL = 300, 900

# No functions or comprehensions: pasted into bench console, they can't see top-level names
for name in frappe.get_all("Root Domain", {"dns_provider": "AWS Route 53"}, pluck="name"):
	domain = RootDomain("Root Domain", name)
	try:
		zone = domain.hosted_zone
	except TypeError:
		print(name, "SKIPPED: no hosted zone")
		continue
	paginator = domain.boto3_client.get_paginator("list_resource_record_sets")
	for page in paginator.paginate(HostedZoneId=zone):
		changes = []
		for record in page["ResourceRecordSets"]:
			if record["Type"] not in ("CNAME", "A") or record.get("TTL") != OLD_TTL:
				continue
			# Route 53 returns "*" as the escape "\052"
			record["Name"] = record["Name"].replace("\\052", "*")
			if not (record["Name"] == f"{name}." or record["Name"].endswith(f".{name}.")):
				continue
			print(name, record["Name"], record["Type"], record["TTL"], "->", NEW_TTL)
			record["TTL"] = NEW_TTL
			changes.append({"Action": "UPSERT", "ResourceRecordSet": record})
		if changes and not DRY_RUN:
			print(
				domain.boto3_client.change_resource_record_sets(
					HostedZoneId=zone, ChangeBatch={"Changes": changes}
				)
			)
