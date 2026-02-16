from typing import TYPE_CHECKING

import frappe

if TYPE_CHECKING:
	from press.press.doctype.database_server.database_server import DatabaseServer

dbs = frappe.get_all(
	"Database Server",
	filters={"has_data_volume": 1, "status": "Active"},
	pluck="name",
)


def execute():
	for db_name in dbs:
		db: DatabaseServer = frappe.get_doc("Database Server", db_name)
		db.add_or_update_mariadb_variable(
			"tmpdir", "value_str", "/opt/volumes/mariadb/tmp", avoid_update_if_exists=True
		)
		print(f"Updated tmpdir of Database Server {db_name}")
