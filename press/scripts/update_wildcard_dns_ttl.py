# In bench IPython console:  %run press/scripts/update_wildcard_dns_ttl.py
# Raises the TTL of the wildcard record (*.<domain>) of every Route 53 Root Domain.
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
	# Route 53 returns "*" as the escape "\052"
	names = (f"\\052.{name}.", f"*.{name}.")
	response = domain.boto3_client.list_resource_record_sets(
		HostedZoneId=zone, StartRecordName=f"*.{name}", MaxItems="10"
	)
	changes = []
	for record in response["ResourceRecordSets"]:
		if record["Name"] in names and record.get("TTL") == OLD_TTL:
			print(name, record["Type"], record["TTL"], "->", NEW_TTL)
			record["Name"] = f"*.{name}."
			record["TTL"] = NEW_TTL
			changes.append({"Action": "UPSERT", "ResourceRecordSet": record})
	if changes:
		print(changes)
	if changes and not DRY_RUN:
		print(
			domain.boto3_client.change_resource_record_sets(
				HostedZoneId=zone, ChangeBatch={"Changes": changes}
			)
		)
