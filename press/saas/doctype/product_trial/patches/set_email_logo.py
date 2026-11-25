import frappe

from press.saas.doctype.product_trial.product_trial import EMAIL_IMAGE_EXTENSIONS


def execute():
	"""Keep raster logos in trial emails. SVG logos need a PNG uploaded by hand."""
	product_trials = frappe.get_all("Product Trial", {"logo": ("is", "set")}, ["name", "logo"])
	for product_trial in product_trials:
		if product_trial.logo.lower().endswith(EMAIL_IMAGE_EXTENSIONS):
			frappe.db.set_value("Product Trial", product_trial.name, "email_logo", product_trial.logo)
