import frappe


@frappe.whitelist(allow_guest=True)
def deploy():
	args = frappe.local.request.args

	apps = args.get("apps")
	source = args.get("source")

	validate_app_list(apps)

	# TODO (WIP):
	# 	1. Check if all apps are valid (fn<validate_app_list>)
	# 	2. Append the "fc_quick_site" custom app (does not exist yet)
	# 	3. Create a new site and set browser cookies
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


def log_traction_source(source):
	pass