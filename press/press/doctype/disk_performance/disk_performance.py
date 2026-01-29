# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import contextlib
import typing

import frappe
from frappe.model.document import Document


class DiskPerformance(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		read_latency_ms: DF.Int
		server: DF.DynamicLink
		server_type: DF.Literal["Server", "Database Server"]
		write_latency_ms: DF.Int
	# end: auto-generated types

	pass


def check_disk_read_write_latency(servers: list, server_type: typing.Literal["app", "db"]):
	"""
	servers: list of servers
	path: path where we can write a small file

	Recommended path for,
		Database Server : /var/lib/mysql
		App Server: /home/frappe
	"""
	from press.press.doctype.ansible_console.ansible_console import AnsibleAdHoc

	if not servers:
		return
	if server_type == "app":
		file_path = "/home/frappe/disk_test.bin"
	elif server_type == "db":
		file_path = "/var/lib/mysql/disk_test.bin"

	runner = AnsibleAdHoc(sources=servers)
	results = runner.run(
		r"dd if=/dev/zero of="
		+ file_path
		+ r" bs=512 count=10  oflag=direct,dsync conv=fdatasync 2>&1 | grep -oP '\d+\.\d+(?= s)' | tr -d '\n'; printf '|'; dd if="
		+ file_path
		+ r" of=/dev/null bs=512 count=10  iflag=direct 2>&1 | grep -oP '\d+\.\d+(?= s)'| tr -d '\n'; (rm "
		+ file_path
		+ r" > /dev/null 2>&1 || true)",
		raw_params=True,
	)

	for result in results:
		with contextlib.suppress(Exception):
			if result["status"] == "Success":
				new_doc_data = {
					"doctype": "Disk Performance",
					"server": result["host"],
					"server_type": "Server" if server_type == "app" else "Database Server",
				}
				output = result["output"].split("|")
				new_doc_data["write_latency_ms"] = int(
					frappe.utils.flt(frappe.utils.flt(output[0], precision=4) * 100)
				)
				new_doc_data["read_latency_ms"] = int(
					frappe.utils.flt(frappe.utils.flt(output[1], precision=4) * 100)
				)

				# Only record if the latency is more than 9ms
				# As per AWS docs, gp3 disks have single-digit latency
				if new_doc_data["write_latency_ms"] > 9 or new_doc_data["read_latency_ms"] > 9:
					frappe.get_doc(new_doc_data).insert()
					frappe.db.commit()
