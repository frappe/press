import re

import frappe

BARE_HOST = re.compile(r"^[a-z0-9-]+(\.[a-z0-9-]+)+(/\S*)?$", re.IGNORECASE)


def execute():
	"""Make each Dashboard Banner help URL start with https:// or http://, or clear it.

	A banner now refuses other help URLs on save. A bare host such as
	`docs.frappe.io/cloud` gets `https://`. Anything else, such as a
	`javascript:` link or a relative path, is cleared.
	"""
	for name, help_url in frappe.get_all(
		"Dashboard Banner", {"help_url": ("is", "set")}, ["name", "help_url"], as_list=True
	):
		fixed = get_fixed_help_url(help_url.strip())
		if fixed != help_url:
			frappe.db.set_value("Dashboard Banner", name, "help_url", fixed, update_modified=False)


def get_fixed_help_url(help_url: str) -> str | None:
	if help_url.lower().startswith(("https://", "http://")):
		scheme, separator, rest = help_url.partition("://")
		return scheme.lower() + separator + rest
	if help_url.startswith("//") and BARE_HOST.match(help_url[2:]):
		return "https:" + help_url
	if BARE_HOST.match(help_url):
		return "https://" + help_url
	return None
