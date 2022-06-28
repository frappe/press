import frappe


def execute():
	frappe.reload_doc("press", "doctype", "virtual_machine_volume")
	frappe.reload_doc("press", "doctype", "virtual_machine")

	for machine in frappe.get_all("Virtual Machine", pluck="name"):
		machine = frappe.get_doc("Virtual Machine", machine)
		for volume in machine.get_volumes():
			row = {
				"aws_volume_id": volume["VolumeId"],
				"volume_type": volume["VolumeType"],
				"size": volume["Size"],
				"iops": volume["Iops"],
			}
			if "Throughput" in volume:
				row["throughput"] = volume["Throughput"]

			machine.append("volumes", row)
		machine.save()
