from __future__ import annotations

import os
import typing

import click
import frappe

if typing.TYPE_CHECKING:
	from press.infrastructure.doctype.arm_build_record.arm_build_record import ARMBuildRecord
	from press.infrastructure.doctype.arm_docker_image.arm_docker_image import ARMDockerImage
	from press.infrastructure.doctype.virtual_machine_migration.virtual_machine_migration import (
		VirtualMachineMigration,
	)
	from press.press.doctype.server.server import Server


arm_machine_mappings = {
	"t2": "t4g",
	"c6i": "c8g",
	"m6i": "m8g",
	"m7i": "m8g",
	"r6i": "r8g",
	# Following are for Zurich due to lack of newer processors in that region
	"r5": "r7g",
	"m5": "m7g",
	"c5": "c7g",
}


def has_arm_build_record(server: str) -> bool:
	return bool(frappe.get_value("ARM Build Record", {"server": server}))


def check_image_build_failure(arm_build_record: ARMBuildRecord) -> bool:
	return any(arm_image.status != "Success" for arm_image in arm_build_record.arm_images)


def create_vmm(server: str, virtual_machine_image: str, target_machine_type: str) -> VirtualMachineMigration:
	virtual_machine_migration: VirtualMachineMigration = frappe.get_doc(
		{
			"doctype": "Virtual Machine Migration",
			"virtual_machine_image": virtual_machine_image,
			"machine_type": target_machine_type,
			"virtual_machine": server,
		}
	)
	return virtual_machine_migration.insert()


def connect(bench_dir, site_dir):
	sites_dir = os.path.join(bench_dir, "sites")
	frappe.init(site=site_dir, sites_path=sites_dir)
	frappe.connect()


def load_servers_from_file(file_path: str) -> list[str]:
	with open(file_path) as server_file:
		return server_file.read().strip().split("\n")


@click.group()
@click.option("--site", "site_name", required=True, help="Frappe site name")
def cli(site_name):
	"""CLI entry point."""
	bench_dir = os.path.dirname(__file__).split("apps")[0]
	site_dir = os.path.join(bench_dir, "sites", site_name)
	connect(bench_dir, site_dir)


@cli.command()
@click.option(
	"--server-file", type=click.Path(exists=True), help="Path to a file containing a list of servers."
)
@click.argument("servers", nargs=-1, type=str)
def trigger_arm_build(servers: list[str], server_file: str):
	"""Trigger ARM build for one or more servers."""
	if server_file:
		servers = load_servers_from_file(server_file)

	for server in servers:
		if has_arm_build_record(server):
			continue

		server: Server = frappe.get_doc("Server", server)
		server.collect_arm_images()
		frappe.db.commit()


@cli.command()
@click.option(
	"--server-file", type=click.Path(exists=True), help="Path to a file containing a list of servers."
)
@click.argument("servers", nargs=-1, type=str)
def pull_images_on_servers(servers: list[str], server_file: str):
	"""Trigger image pulls on Intel server to be converted"""
	if server_file:
		servers = load_servers_from_file(server_file)

	for server in servers:
		arm_build_record: ARMBuildRecord = frappe.get_doc("ARM Build Record", {"server": server})

		try:
			arm_build_record.pull_images()
			print(f"Pulled image on {server}")
		except frappe.ValidationError:
			print(f"Skipping server {server} due to failed builds")

		frappe.db.commit()


@cli.command()
@click.option("--vmi", default="f377-mumbai.frappe.cloud")
@click.option("--vmi-cluster", required=True)
@click.option(
	"--server-file", type=click.Path(exists=True), help="Path to a file containing a list of servers."
)
@click.argument("servers", nargs=-1, type=str)
def update_image_and_create_migration(
	vmi: str,
	vmi_cluster: str,
	servers: list[str],
	server_file: str,
):
	"""Update docker image on bench config and create virtual machine migration"""
	vmi = frappe.get_value("Virtual Machine Image", {"virtual_machine": vmi, "cluster": vmi_cluster}, "name")
	if not vmi:
		print(f"Aborting VMI not found {vmi}!")
		return

	if server_file:
		servers = load_servers_from_file(server_file)

	for server in servers:
		arm_build_record: ARMBuildRecord = frappe.get_doc("ARM Build Record", {"server": server})
		try:
			arm_build_record.update_image_tags_on_benches()
			machine_type = frappe.db.get_value("Virtual Machine", {"name": server}, "machine_type")
			machine_series, machine_size = machine_type.split(".")
			virtual_machine_migration: VirtualMachineMigration = create_vmm(
				server=server,
				virtual_machine_image=vmi,
				target_machine_type=f"{arm_machine_mappings[machine_series]}.{machine_size}",
			)
			frappe.db.commit()
			print(f"Created {virtual_machine_migration.name}")
		except frappe.ValidationError as e:
			print(f"Aborting: {e}!")
			break


@cli.command()
@click.option(
	"--server-file", type=click.Path(exists=True), help="Path to a file containing a list of servers."
)
@click.argument("servers", nargs=-1, type=str)
def arm_build_info(servers: list[str], server_file: str):
	total, successful, failed, running = 0, 0, 0, 0
	if server_file:
		servers = load_servers_from_file(server_file)

	def _status_info(images: list[ARMDockerImage], status: str):
		return len([image for image in images if image.status == status])

	for server in servers:
		arm_build_record: ARMBuildRecord = frappe.get_doc("ARM Build Record", {"server": server})
		arm_build_record.sync_status()
		total += len(arm_build_record.arm_images)
		running += _status_info(arm_build_record.arm_images, "Running")
		successful += _status_info(arm_build_record.arm_images, "Success")
		failed += _status_info(arm_build_record.arm_images, "Failure")

	print(f"Total: {total}\nSuccessful: {successful}\nRunning: {running}\nFailed: {failed}")


@cli.result_callback()
def cleanup(*args, **kwargs):
	frappe.destroy()


def main():
	cli(obj={})


if __name__ == "__main__":
	main()
