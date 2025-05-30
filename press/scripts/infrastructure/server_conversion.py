from __future__ import annotations

import os
import typing

import click
import frappe

if typing.TYPE_CHECKING:
	from press.infrastructure.doctype.arm_build_record.arm_build_record import ARMBuildRecord
	from press.press.doctype.server.server import Server


def has_arm_build_record(server: str) -> bool:
	return bool(frappe.get_value("ARM Build Record", {"server": server}))


def check_image_build_failure(arm_build_record: ARMBuildRecord) -> bool:
	return any(arm_image.status != "Success" for arm_image in arm_build_record.arm_images)


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
@click.argument("servers", nargs=-1, type=str)
def update_docker_image_in_conf(servers: list[str]):
	for server in servers:
		arm_build_record: ARMBuildRecord = frappe.get_doc("ARM Build Record", {"server": server})
		try:
			arm_build_record.update_image_tags_on_benches()
			print(f"Update config for {server}")
		except frappe.ValidationError as e:
			print(e)
			break


@cli.result_callback()
def cleanup(*args, **kwargs):
	frappe.destroy()


def main():
	cli(obj={})


if __name__ == "__main__":
	main()
