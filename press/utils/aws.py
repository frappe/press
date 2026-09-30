import frappe

# Bahrain (unreachable from Press infra), Beijing (separate AWS China partition, priced in CNY).
EXCLUDED_REGIONS = ["me-south-1", "cn-north-1"]


def get_press_aws_credentials():
	settings = frappe.get_single("Press Settings")
	secret_key = settings.get_password("aws_secret_access_key", raise_exception=False)
	if not settings.aws_access_key_id or not secret_key:
		frappe.throw("AWS credentials are not configured in Press Settings")

	return {
		"aws_access_key_id": settings.aws_access_key_id,
		"aws_secret_access_key": secret_key,
	}
