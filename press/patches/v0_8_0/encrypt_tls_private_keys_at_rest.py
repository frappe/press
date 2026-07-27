import frappe
from frappe.utils.password import set_encrypted_password

BATCH_SIZE = 500


def execute():
	"""Move existing plaintext TLS private keys into the encrypted `__Auth` store.

	`private_key` was a Code field (plaintext in the DB). It is now a Password
	field, encrypted at rest. The doctype sync only alters the column type; it
	does not move the existing values. Read each row's raw column (bypassing the
	ORM so we get the real key, not the dummy mask), encrypt it into `__Auth`,
	and overwrite the column with the mask Frappe expects for a Password field.

	Runs in batches and commits after each one. There are thousands of these in
	prod; a single transaction over all rows would hold locks for the whole run
	and lose all progress on failure. The batch filter skips already-masked rows
	(a run of asterisks), so the patch is also resumable if interrupted.
	"""
	while True:
		rows = frappe.db.sql(
			"""
			SELECT name, private_key
			FROM `tabTLS Certificate`
			WHERE private_key IS NOT NULL
				AND private_key != ''
				AND private_key NOT REGEXP '^[*]+$'
			LIMIT %s
			""",
			BATCH_SIZE,
			as_dict=True,
		)
		if not rows:
			break
		for row in rows:
			key = row.private_key
			set_encrypted_password("TLS Certificate", row.name, key, "private_key")
			frappe.db.set_value(
				"TLS Certificate", row.name, "private_key", "*" * len(key), update_modified=False
			)
		frappe.db.commit()
