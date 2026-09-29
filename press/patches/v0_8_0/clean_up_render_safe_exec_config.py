import frappe

KEY = "disable_render_safe_exec"


def execute():
	# Private bench owners can set this key in bench config. Site.update_config blocks it on public benches
	frappe.db.delete("Site Config Key Blacklist", {"key": KEY})
	remove_duplicate_config_rows()


def remove_duplicate_config_rows():
	"""Each dashboard config save doubled the blacklisted rows of a group. Keep one row of the key."""
	# Delete a row if another row of the same group has a smaller name
	frappe.db.sql(
		"""
		delete row from `tabCommon Site Config` row
		join `tabCommon Site Config` other
			on other.parenttype = row.parenttype
			and other.parent = row.parent
			and other.`key` = row.`key`
			and other.name < row.name
		where row.parenttype = 'Release Group' and row.`key` = %s
		""",
		KEY,
	)
