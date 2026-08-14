import frappe
from frappe.utils.password import set_encrypted_password

BATCH_SIZE = 500


def is_masked(value: str) -> bool:
	"""A Password field stores a run of asterisks in the main column."""
	return set(value) == {"*"}


def execute():
	"""Move existing plaintext TLS private keys into the encrypted `__Auth` store.

	`private_key` was a Code field (plaintext in the DB) and becomes a Password
	field, encrypted at rest, once the model sync (which runs after this patch)
	alters it. Read each row's plaintext value, encrypt it into `__Auth`, and
	overwrite the column with the dummy mask Frappe expects for a Password field.

	Runs in batches and commits after each one. There are thousands of these in
	prod; a single transaction over all rows would hold locks for the whole run
	and lose all progress on failure. Already-masked rows are skipped, so the
	patch is idempotent and resumable if interrupted.
	"""
	cursor = ""
	while True:
		rows = frappe.get_all(
			"TLS Certificate",
			filters={"name": (">", cursor)},
			fields=["name", "private_key"],
			order_by="name asc",
			limit=BATCH_SIZE,
		)
		if not rows:
			break
		cursor = rows[-1].name
		for row in rows:
			key = row.private_key
			if not key or is_masked(key):
				continue
			set_encrypted_password("TLS Certificate", row.name, key, "private_key")
			frappe.db.set_value(
				"TLS Certificate", row.name, "private_key", "*" * len(key), update_modified=False
			)
		frappe.db.commit()
