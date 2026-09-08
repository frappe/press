import frappe

# Bahrain (unreachable from Press infra), Beijing (separate AWS China partition, priced in CNY).
EXCLUDED_REGIONS = ["me-south-1", "cn-north-1"]

# Cost Explorer reports a usage type, not a region, and the region is folded into the
# usage type as a short prefix ("APS3-TimedStorage-ByteHrs"). The prefixes are AWS's own
# and do not follow from the region name, so they have to be spelled out. A usage type
# with no prefix is us-east-1; an unrecognized prefix is kept verbatim rather than guessed.
USAGE_TYPE_REGION_PREFIXES = {
	"USE1": "us-east-1",
	"USE2": "us-east-2",
	"USW1": "us-west-1",
	"USW2": "us-west-2",
	"CAN1": "ca-central-1",
	"SAE1": "sa-east-1",
	"EU": "eu-west-1",
	"EUW1": "eu-west-1",
	"EUW2": "eu-west-2",
	"EUW3": "eu-west-3",
	"EUC1": "eu-central-1",
	"EUN1": "eu-north-1",
	"EUS1": "eu-south-1",
	"APN1": "ap-northeast-1",
	"APN2": "ap-northeast-2",
	"APN3": "ap-northeast-3",
	"APS1": "ap-southeast-1",
	"APS2": "ap-southeast-2",
	"APS3": "ap-south-1",
	"APS4": "ap-southeast-3",
	"APS5": "ap-south-2",
	"APE1": "ap-east-1",
	"AFS1": "af-south-1",
	"MES1": "me-south-1",
}


def get_press_aws_credentials():
	settings = frappe.get_single("Press Settings")
	secret_key = settings.get_password("aws_secret_access_key", raise_exception=False)
	if not settings.aws_access_key_id or not secret_key:
		frappe.throw("AWS credentials are not configured in Press Settings")

	return {
		"aws_access_key_id": settings.aws_access_key_id,
		"aws_secret_access_key": secret_key,
	}


def get_cluster_aws_credentials(cluster_name):
	cluster = frappe.get_doc("Cluster", cluster_name)
	secret_key = cluster.get_password("aws_secret_access_key", raise_exception=False)
	if not cluster.aws_access_key_id or not secret_key:
		frappe.throw(f"AWS credentials are not configured on Cluster {cluster_name}")

	return {
		"aws_access_key_id": cluster.aws_access_key_id,
		"aws_secret_access_key": secret_key,
	}


def region_from_usage_type(usage_type):
	"""Best-effort region behind a Cost Explorer usage type. Empty when the usage type
	carries no region at all, which is true of global services like Route 53."""
	if not usage_type:
		return ""

	prefix, separator, _ = usage_type.partition("-")
	if not separator:
		# Unprefixed usage types ("DataTransfer-Out-Bytes") are us-east-1 by AWS convention.
		return "us-east-1"
	if prefix in USAGE_TYPE_REGION_PREFIXES:
		return USAGE_TYPE_REGION_PREFIXES[prefix]
	if prefix.isupper() and len(prefix) <= 5:
		return prefix
	return "us-east-1"
