import frappe


def execute():
	# Private bench owners can set this key in bench config. Site.update_config blocks it on public benches
	frappe.db.delete("Site Config Key Blacklist", {"key": "disable_render_safe_exec"})
	remove_duplicate_config_rows()


def remove_duplicate_config_rows():
	"""Each dashboard config save doubled the blacklisted rows of a group. Keep one row of each key."""
	frappe.db.sql(
		"""
		delete copy from `tabCommon Site Config` copy
		join `tabCommon Site Config` kept
			on kept.parenttype = copy.parenttype
			and kept.parent = copy.parent
			and kept.`key` = copy.`key`
			and kept.name < copy.name
		where copy.parenttype = 'Release Group'
		"""
	)
