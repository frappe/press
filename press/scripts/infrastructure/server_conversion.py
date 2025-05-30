from __future__ import annotations

import os
import typing

import click
import frappe

if typing.TYPE_CHECKING:
	from press.infrastructure.doctype.arm_build_record.arm_build_record import ARMBuildRecord
	from press.infrastructure.doctype.virtual_machine_migration.virtual_machine_migration import (
		VirtualMachineMigration,
	)
	from press.press.doctype.server.server import Server


arm_machine_mappings = {
	"t2.medium": "t4g.medium",
	"c6i.large": "c8g.large",
	"m6i.large": "m8g.large",
	"m7i.large": "m8g.large",
	"c6i.xlarge": "c8g.xlarge",
	"m6i.xlarge": "m8g.xlarge",
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


@click.group()
@click.option("--site", "site_name", required=True, help="Frappe site name")
def cli(site_name):
	"""CLI entry point."""
	bench_dir = os.path.dirname(__file__).split("apps")[0]
	site_dir = os.path.join(bench_dir, "sites", site_name)
	connect(bench_dir, site_dir)


@cli.command()
@click.argument("servers", nargs=-1, type=str)
def trigger_arm_build(servers: list[str]):
	"""Trigger ARM build for one or more servers."""
	for server in servers:
		if has_arm_build_record(server):
			continue

		server: Server = frappe.get_doc("Server", server)
		server.collect_arm_images()
		frappe.db.commit()


@cli.command()
@click.argument("servers", nargs=-1, type=str)
def pull_images_on_servers(servers: list[str]):
	"""Trigger image pulls on Intel server to be converted"""
	for server in servers:
		arm_build_record: ARMBuildRecord = frappe.get_doc("ARM Build Record", {"server": server})
		arm_build_record.sync_status()
		has_failed_builds = check_image_build_failure(arm_build_record)

		if has_failed_builds:
			print(f"Has Failed ARM Builds: {arm_build_record.name}")
			continue

		print(f"Pull image on server: {server}")
		arm_build_record.pull_images()
		frappe.db.commit()


@cli.command()
@click.option("--vmi", default="f377-mumbai.frappe.cloud")
@click.argument("servers", nargs=-1, type=list[str])
def update_image_and_create_migration(vmi: str, servers: list[str]):
	"""Update docker image on bench config and create virtual machine migration"""
	vmi = frappe.get_value("Virtual Machine Image", {"virtual_machine": vmi}, "name")
	if not vmi:
		print(f"Aborting VMI not found {vmi}!")
		return
	for server in servers:
		arm_build_record: ARMBuildRecord = frappe.get_doc("ARM Build Record", {"server": server})
		try:
			arm_build_record.update_image_tags_on_benches()
			machine_type = frappe.db.get_value("Virtual Machine", {"name": server}, "machine_type")
			virtual_machine_migration: VirtualMachineMigration = create_vmm(
				server=server,
				virtual_machine_image=vmi,
				target_machine_type=arm_machine_mappings[machine_type],
			)
			frappe.db.commit()
			print(f"Created {virtual_machine_migration.name}")
		except frappe.ValidationError as e:
			print(f"Aborting: {e}!")
			break


@cli.command()
@click.argument("servers", nargs=-1, type=list[str])
def start_active_benches_on_servers(servers: list[str]):
	"""Start docker containers post migration"""
	for server in servers:
		server: Server = frappe.get_doc("Server", server)
		server.start_active_benches()


@cli.result_callback()
def cleanup(*args, **kwargs):
	frappe.destroy()


def main():
	cli(obj={})


if __name__ == "__main__":
	main()
