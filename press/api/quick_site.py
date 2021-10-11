import frappe

from frappe.utils import comma_and
from press.experimental.doctype.feature_traction.feature_traction import (
	log_feature_traction,
)


@frappe.whitelist(allow_guest=True)
def deploy():
	args = frappe.local.request.args

	apps = args.get("apps")
	source = args.get("source")

	log_data = f"""
Quick Deploy Method\n
Apps to be installed: {apps}
"""
	log_feature_traction(
		title="Try on FC Button",
		source=source,
		log=log_data,
		path=getattr(frappe.request, "full_path", "NOTFOUND"),
	)

	redirect_to_home()


def validate_app_list(apps: str):
	if not apps:
		frappe.throw("Param 'apps' is required!")

	apps = apps.split(",")
	apps_set = set(apps)
	all_apps_set = set(frappe.get_all("App", pluck="name"))
	non_existing_apps = apps_set - all_apps_set

	if len(non_existing_apps) > 0:
		non_existing_apps = comma_and(non_existing_apps)
		frappe.throw(
			f"App(s) {frappe.bold(non_existing_apps)} do not exist! Please check app name."
		)


def redirect_to_home():
	frappe.local.response["type"] = "redirect"
	frappe.local.response["location"] = "/"
	frappe.db.commit()
