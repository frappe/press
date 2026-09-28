import frappe


def execute():
	# Private bench owners can set this key in bench config. Site.update_config blocks it on public benches
	frappe.db.delete("Site Config Key Blacklist", {"key": "disable_render_safe_exec"})
	remove_duplicate_config_rows()


def remove_duplicate_config_rows():
	"""Each dashboard config save doubled the blacklisted rows of a group.
	Keep the last copy of each key, because the last copy is the value in common_site_config."""
	rows = frappe.get_all(
		"Common Site Config",
		filters={"parenttype": "Release Group"},
		fields=["name", "parent", "`key`"],
		order_by="parent, idx",
	)
	last_copy = {(row.parent, row.key): row.name for row in rows}
	extra_copies = [row.name for row in rows if last_copy[(row.parent, row.key)] != row.name]
	if extra_copies:
		frappe.db.delete("Common Site Config", {"name": ("in", extra_copies)})
