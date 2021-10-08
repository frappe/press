import frappe

from frappe.utils import comma_and


@frappe.whitelist(allow_guest=True)
def deploy():
	args = frappe.local.request.args

	apps = args.get("apps")
	source = args.get("source")

	validate_app_list(apps)

	# TODO (WIP):
	# 	1. Check if all apps are valid (fn<validate_app_list>)
	# 	2. Append the "fc_quick_site" custom app (does not exist yet)
	# 	3. Create a new site and set browser cookies (or maybe localStorage)
	# 		a. Check out: frappe.local.cookie_manager.set_cookie
	# 		b. Check out: Site "sid" etc.
	# 		c. Mark the site 'Quick deploy' (flag in doctype?)
	# [TBD]

	if source:
		log_traction_source(source)

	return {"apps": apps.split(","), "source": source}


def validate_app_list(apps):
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


def log_traction_source(source):
	pass