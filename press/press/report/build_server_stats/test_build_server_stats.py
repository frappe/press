# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

from datetime import datetime
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.cluster.test_cluster import create_test_cluster
from press.press.doctype.server.test_server import create_test_server
from press.press.report.build_server_stats.build_server_stats import (
	CHARTS,
	DiskUsage,
	Period,
	floor_to_bucket,
	get_chart,
	get_charts,
	get_period,
	get_selected_chart,
	group_by_server,
	last_number,
	one_mountpoint_per_device,
	percentile,
	seconds_of,
)


def build(server="f1.frappe.cloud", **stamps):
	return frappe._dict({"build_server": server, "status": "Success", **stamps})


class TestBuildSpans(FrappeTestCase):
	def test_a_build_reports_the_seconds_between_its_two_stamps(self):
		builds = [
			build(
				build_start=datetime(2026, 9, 10, 10, 0, 0),
				build_end=datetime(2026, 9, 10, 10, 5, 30),
			)
		]

		self.assertEqual(seconds_of(builds, "build_start", "build_end"), [330])

	def test_a_build_that_has_not_finished_is_left_out(self):
		builds = [build(build_start=datetime(2026, 9, 10, 10, 0, 0), build_end=None)]

		self.assertEqual(seconds_of(builds, "build_start", "build_end"), [])

	def test_builds_are_grouped_under_the_server_that_ran_them(self):
		grouped = group_by_server([build(server="f1.frappe.cloud"), build(server="f2.frappe.cloud")])

		self.assertEqual(sorted(grouped), ["f1.frappe.cloud", "f2.frappe.cloud"])
		self.assertEqual(len(grouped["f1.frappe.cloud"]), 1)


class TestPercentile(FrappeTestCase):
	def test_the_median_of_five_values_is_the_middle_one(self):
		self.assertEqual(percentile([50, 10, 30, 20, 40], 0.5), 30)

	def test_the_p95_of_a_short_list_is_the_largest_value(self):
		self.assertEqual(percentile([10, 20, 30], 0.95), 30)

	def test_a_window_without_builds_reports_zero(self):
		self.assertEqual(percentile([], 0.5), 0)


class TestLastNumber(FrappeTestCase):
	def test_the_last_point_of_a_series_is_the_value(self):
		self.assertEqual(last_number([1.0, 2.0, 3.5]), 3.5)

	def test_a_series_that_ends_in_a_nan_reads_as_zero(self):
		self.assertEqual(last_number([1.0, float("nan")]), 0)

	def test_a_series_without_points_reads_as_zero(self):
		self.assertEqual(last_number([]), 0)


class TestChart(FrappeTestCase):
	def test_builds_in_the_same_bucket_share_one_bar(self):
		builds = [
			build(build_start=datetime(2026, 9, 10, 10, 0, 10)),
			build(build_start=datetime(2026, 9, 10, 10, 4, 50)),
			build(build_start=datetime(2026, 9, 10, 10, 6, 0)),
		]

		chart = get_chart(3600, builds)

		self.assertEqual(chart["title"], "Builds started per 5 minutes")
		self.assertEqual(chart["data"]["datasets"][0]["values"], [2, 1])

	def test_a_window_without_builds_gives_an_empty_chart(self):
		chart = get_chart(3600, [])

		self.assertEqual(chart["data"]["labels"], [])

	def test_a_stamp_is_floored_to_the_start_of_its_bucket(self):
		floored = floor_to_bucket(datetime(2026, 9, 10, 10, 7, 42), 300)

		self.assertEqual(floored.minute, 5)
		self.assertEqual(floored.second, 0)


class TestBuildsByClusterChart(FrappeTestCase):
	def test_builds_of_every_status_are_stacked_by_the_cluster_of_their_build_server(self):
		servers = [
			frappe._dict(name="f1.frappe.cloud", cluster="Mumbai"),
			frappe._dict(name="f2.frappe.cloud", cluster="Default"),
		]
		start = datetime(2026, 9, 10, 10, 0, 10)
		builds = [
			build("f1.frappe.cloud", status="Success", build_start=start),
			build("f1.frappe.cloud", status="Failure", build_start=start),
			build("f2.frappe.cloud", status="Running", build_start=datetime(2026, 9, 10, 10, 6, 0)),
		]

		period = Period(datetime(2026, 9, 10, 10, 0), datetime(2026, 9, 10, 11, 0))
		datasets = get_selected_chart("Builds by Cluster", period, builds, servers)["data"]["datasets"]

		self.assertEqual(
			{dataset["name"]: dataset["values"] for dataset in datasets},
			{"Default": [0, 1], "Mumbai": [2, 0]},
		)


class TestOneMountpointPerDevice(FrappeTestCase):
	def test_bind_mounts_drop_out_and_a_disk_shows_under_its_volume_path_else_its_shortest(self):
		used = {
			("f1.frappe.cloud", "/dev/sda1", "/"): 55.0,
			("f1.frappe.cloud", "/dev/sdb", "/home/frappe/mnt/builds"): 87.5,
			("f1.frappe.cloud", "/dev/sdb", "/home/frappe/mnt/builds/tmp/buildkit-mount1085636546"): 87.6,
			("f1.frappe.cloud", "/dev/sdc", "/opt/volumes/benches"): 71.3,
			("f1.frappe.cloud", "/dev/sdc", "/home/frappe/benches"): 71.3,
			("f1.frappe.cloud", "/dev/sdc", "/var/lib/docker"): 71.3,
		}

		self.assertEqual(
			one_mountpoint_per_device(used, ["f1.frappe.cloud"]),
			{"f1.frappe.cloud": {"/": 55.0, "/opt/volumes/benches": 71.3, "/home/frappe/mnt/builds": 87.5}},
		)

	def test_the_same_device_name_on_two_servers_is_two_disks(self):
		used = {("f1.frappe.cloud", "/dev/sda1", "/"): 40.0, ("f2.frappe.cloud", "/dev/sda1", "/"): 60.0}

		self.assertEqual(
			one_mountpoint_per_device(used, ["f1.frappe.cloud", "f2.frappe.cloud"]),
			{"f1.frappe.cloud": {"/": 40.0}, "f2.frappe.cloud": {"/": 60.0}},
		)


class TestAgentJobFailureCharts(FrappeTestCase):
	def setUp(self):
		self.period = get_period(
			frappe._dict(from_datetime="2026-09-10 10:00:00", to_datetime="2026-09-10 11:00:00")
		)

	def tearDown(self):
		frappe.db.rollback()

	def job(self, server, job_type, status, creation="2026-09-10 10:01:00", end=None, start=None):
		frappe.get_doc(
			{
				"doctype": "Agent Job",
				"server_type": "Server",
				"server": server,
				"job_type": job_type,
				"status": status,
				"creation": creation,
				"start": start,
				"end": end,
			}
		).db_insert()

	def datasets(self, chart):
		chart = get_selected_chart(chart, self.period, [], [])
		return {dataset["name"]: dataset["values"] for dataset in chart["data"]["datasets"]}

	def test_failed_and_undelivered_new_bench_jobs_are_stacked_by_the_cluster_of_their_server(self):
		mumbai = create_test_server(cluster="Mumbai").name
		self.job(mumbai, "New Bench", "Failure")
		self.job(mumbai, "New Bench", "Delivery Failure")
		self.job(mumbai, "New Bench", "Success")
		self.job(mumbai, "New Bench", "Failure", creation="2026-09-10 09:00:00")

		self.assertEqual(self.datasets("New Bench Failures by Cluster"), {"Mumbai": [2]})

	def test_failed_remote_builder_jobs_are_stacked_by_build_server_and_other_job_types_are_left_out(self):
		self.job("f1.frappe.cloud", "Run Remote Builder", "Failure")
		self.job("f2.frappe.cloud", "Run Remote Builder", "Failure")
		self.job("f2.frappe.cloud", "New Bench", "Failure")

		self.assertEqual(
			self.datasets("Remote Builder Failures by Build Server"),
			{"f1.frappe.cloud": [1], "f2.frappe.cloud": [1]},
		)

	def test_a_failed_job_counts_when_it_ended_not_when_it_was_created(self):
		self.job(
			"f1.frappe.cloud", "Run Remote Builder", "Failure", "2026-09-10 09:30:00", "2026-09-10 10:20:00"
		)
		self.job(
			"f2.frappe.cloud", "Run Remote Builder", "Failure", "2026-09-10 10:50:00", "2026-09-10 11:40:00"
		)

		self.assertEqual(self.datasets("Remote Builder Failures by Build Server"), {"f1.frappe.cloud": [1]})

	def test_a_job_that_waited_two_days_before_it_failed_still_counts_when_it_ended(self):
		self.job(
			"f1.frappe.cloud", "Run Remote Builder", "Failure", "2026-09-08 10:30:00", "2026-09-10 10:20:00"
		)

		self.assertEqual(self.datasets("Remote Builder Failures by Build Server"), {"f1.frappe.cloud": [1]})

	def test_every_chart_is_sent_with_builds_started_first_and_the_rest_named_under_it(self):
		chart = get_charts(self.period, [], [])

		self.assertEqual(chart["name"], "Builds Started")
		self.assertEqual([extra["name"] for extra in chart["charts"]], list(CHARTS[1:]))

	def test_new_bench_jobs_in_the_period_are_stacked_by_status(self):
		self.job("f1.frappe.cloud", "New Bench", "Success")
		self.job("f1.frappe.cloud", "New Bench", "Success")
		self.job("f1.frappe.cloud", "New Bench", "Failure")
		self.job("f1.frappe.cloud", "New Bench", "Success", creation="2026-09-10 09:00:00")
		self.job("f1.frappe.cloud", "Archive Bench", "Success")

		self.assertEqual(self.datasets("New Bench Jobs by Status"), {"Failure": [1], "Success": [2]})

	def test_new_bench_jobs_of_every_status_are_stacked_by_the_cluster_of_their_server(self):
		mumbai = create_test_server(cluster="Mumbai").name
		frankfurt = create_test_server(cluster=create_test_cluster("Frankfurt", "eu-central-1").name).name
		self.job(mumbai, "New Bench", "Success")
		self.job(mumbai, "New Bench", "Failure")
		self.job(frankfurt, "New Bench", "Running")
		self.job(frankfurt, "New Bench", "Success", creation="2026-09-10 09:00:00")
		self.job(frankfurt, "Archive Bench", "Success")

		self.assertEqual(self.datasets("New Bench Jobs by Cluster"), {"Frankfurt": [1], "Mumbai": [2]})

	def build(self, server, status, creation):
		frappe.get_doc(
			{
				"doctype": "Deploy Candidate Build",
				"build_server": server,
				"status": status,
				"creation": creation,
			}
		).db_insert()

	def test_failed_builds_are_stacked_by_build_server_at_their_creation(self):
		self.build("f1.frappe.cloud", "Failure", "2026-09-10 10:01:00")
		self.build("f2.frappe.cloud", "Failure", "2026-09-10 10:01:00")
		self.build("f2.frappe.cloud", "Success", "2026-09-10 10:01:00")
		self.build("f2.frappe.cloud", "Failure", "2026-09-10 09:00:00")

		self.assertEqual(
			self.datasets("Build Failures by Build Server"), {"f1.frappe.cloud": [1], "f2.frappe.cloud": [1]}
		)

	def test_failed_builds_are_stacked_by_the_cluster_of_their_build_server_at_their_creation(self):
		mumbai = create_test_server(cluster="Mumbai").name
		frankfurt = create_test_server(cluster=create_test_cluster("Frankfurt", "eu-central-1").name).name
		self.build(mumbai, "Failure", "2026-09-10 10:01:00")
		self.build(mumbai, "Failure", "2026-09-10 10:02:00")
		self.build(frankfurt, "Failure", "2026-09-10 10:31:00")
		self.build(frankfurt, "Success", "2026-09-10 10:31:00")
		self.build(frankfurt, "Failure", "2026-09-10 09:58:00")

		self.assertEqual(self.datasets("Build Failures by Cluster"), {"Frankfurt": [0, 1], "Mumbai": [2, 0]})

	def test_successful_new_bench_jobs_that_ended_in_the_period_fall_into_minute_bins_by_cluster(self):
		mumbai = create_test_server(cluster="Mumbai").name
		frankfurt = create_test_server(cluster=create_test_cluster("Frankfurt", "eu-central-1").name).name
		for server, status, start, end in [
			(mumbai, "Success", "2026-09-10 10:00:00", "2026-09-10 10:02:30"),
			(mumbai, "Success", "2026-09-10 10:10:00", "2026-09-10 10:22:00"),
			(frankfurt, "Success", "2026-09-10 10:00:00", "2026-09-10 10:03:00"),
			(frankfurt, "Failure", "2026-09-10 10:00:00", "2026-09-10 10:01:00"),
			(frankfurt, "Success", "2026-09-10 09:00:00", "2026-09-10 09:05:00"),
		]:
			self.job(server, "New Bench", status, start, end=end, start=start)

		chart = get_selected_chart("New Bench Duration by Cluster", self.period, [], [])

		self.assertEqual(chart["data"]["labels"][:2], ["0-1 min", "1-2 min"])
		datasets = {dataset["name"]: dataset["values"] for dataset in chart["data"]["datasets"]}
		self.assertEqual(datasets["Mumbai"], [0, 0, 1] + [0] * 9 + [1])
		self.assertEqual(datasets["Frankfurt"], [0, 0, 0, 1] + [0] * 9)

	def test_docker_and_registry_prune_plays_are_stacked_by_server_and_other_plays_are_left_out(self):
		for server, playbook, creation in [
			("f1.frappe.cloud", "docker_system_prune.yml", "2026-09-10 10:01:00"),
			("f1.frappe.cloud", "docker_system_prune.yml", "2026-09-10 10:02:00"),
			("r1.frappe.cloud", "prune_mirror_registry.yml", "2026-09-10 10:01:00"),
			("f1.frappe.cloud", "server.yml", "2026-09-10 10:01:00"),
			("f1.frappe.cloud", "docker_system_prune.yml", "2026-09-10 09:00:00"),
		]:
			frappe.get_doc(
				{
					"doctype": "Ansible Play",
					"server_type": "Server",
					"server": server,
					"playbook": playbook,
					"creation": creation,
				}
			).db_insert()

		self.assertEqual(
			self.datasets("Prune Jobs by Server"), {"f1.frappe.cloud": [2], "r1.frappe.cloud": [1]}
		)


class TestBuildDurationChart(FrappeTestCase):
	def test_successful_builds_fall_into_minute_bins_stacked_by_build_server(self):
		start = datetime(2026, 9, 10, 10, 0)
		builds = [
			build("f1.frappe.cloud", build_start=start, build_end=datetime(2026, 9, 10, 10, 5)),
			build("f2.frappe.cloud", build_start=start, build_end=datetime(2026, 9, 10, 10, 30)),
			build("f2.frappe.cloud", build_start=start, build_end=datetime(2026, 9, 10, 11, 0)),
			build("f1.frappe.cloud", build_start=start, build_end=None),
		]
		builds.append(frappe._dict(builds[0], status="Failure"))

		chart = get_selected_chart("Build Duration by Build Server", None, builds, [])

		self.assertEqual(chart["data"]["labels"][:2], ["0-5 min", "5-10 min"])
		self.assertEqual(len(chart["data"]["labels"]), 13)
		datasets = {dataset["name"]: dataset["values"] for dataset in chart["data"]["datasets"]}
		self.assertEqual(datasets["f1.frappe.cloud"], [0, 1] + [0] * 11)
		self.assertEqual(datasets["f2.frappe.cloud"], [0] * 6 + [1] + [0] * 5 + [1])

	def test_successful_builds_fall_into_minute_bins_stacked_by_the_cluster_of_their_build_server(self):
		servers = [
			frappe._dict(name="f1.frappe.cloud", cluster="Mumbai"),
			frappe._dict(name="f2.frappe.cloud", cluster="Mumbai"),
		]
		start = datetime(2026, 9, 10, 10, 0)
		builds = [
			build("f1.frappe.cloud", build_start=start, build_end=datetime(2026, 9, 10, 10, 5)),
			build("f2.frappe.cloud", build_start=start, build_end=datetime(2026, 9, 10, 10, 7)),
			build("gone.frappe.cloud", build_start=start, build_end=datetime(2026, 9, 10, 11, 0)),
		]

		chart = get_selected_chart("Build Duration by Cluster", None, builds, servers)

		datasets = {dataset["name"]: dataset["values"] for dataset in chart["data"]["datasets"]}
		self.assertEqual(datasets["Mumbai"], [0, 2] + [0] * 11)
		self.assertEqual(datasets["No cluster"], [0] * 12 + [1])


class TestPeriod(FrappeTestCase):
	def test_from_and_to_set_the_period_and_the_duration_is_ignored(self):
		period = get_period(
			frappe._dict(
				from_datetime="2026-09-10 10:00:00", to_datetime="2026-09-10 12:30:00", duration="1 hour"
			)
		)

		self.assertEqual(period.start, datetime(2026, 9, 10, 10, 0, 0))
		self.assertEqual(period.end, datetime(2026, 9, 10, 12, 30, 0))
		self.assertEqual(period.seconds, 9000)

	def test_a_to_without_a_from_counts_the_duration_back_from_to(self):
		period = get_period(frappe._dict(to_datetime="2026-09-10 12:00:00", duration="3 hours"))

		self.assertEqual(period.start, datetime(2026, 9, 10, 9, 0, 0))

	def test_without_from_or_to_the_duration_ends_now(self):
		period = get_period(frappe._dict(duration="15 minutes"))

		self.assertEqual(period.seconds, 15 * 60)
		self.assertLess((datetime.now() - period.end).total_seconds(), 60)

	def test_a_from_after_the_to_is_rejected(self):
		with self.assertRaisesRegex(frappe.ValidationError, "The period must be at least 5 minutes long"):
			get_period(frappe._dict(from_datetime="2026-09-10 12:00:00", to_datetime="2026-09-10 10:00:00"))

	def test_a_period_too_short_for_two_prometheus_scrapes_is_rejected(self):
		with self.assertRaisesRegex(frappe.ValidationError, "The period must be at least 5 minutes long"):
			get_period(frappe._dict(from_datetime="2026-09-10 12:00:00", to_datetime="2026-09-10 12:00:01"))

	def test_a_period_of_exactly_five_minutes_is_accepted(self):
		period = get_period(
			frappe._dict(from_datetime="2026-09-10 12:00:00", to_datetime="2026-09-10 12:05:00")
		)

		self.assertEqual(period.seconds, 300)


class TestDiskUsage(FrappeTestCase):
	def disk_usage(self, used):
		with patch(
			"press.press.report.build_server_stats.build_server_stats.get_fleet_disk_usage", return_value=used
		):
			return DiskUsage(list(used), datetime(2026, 9, 10))

	def test_a_mountpoint_on_two_servers_gets_its_own_column_and_a_lone_one_stays_in_other(self):
		disk = self.disk_usage(
			{
				"f1.frappe.cloud": {"/": 40.0, "/opt/volumes/docker": 88.0},
				"f2.frappe.cloud": {"/": 55.0, "/home/registry": 70.0},
			}
		)

		self.assertEqual([column["fieldname"] for column in disk.columns()], ["disk_0", "disk"])
		self.assertEqual(disk.cells("f1.frappe.cloud"), {"disk_0": 40.0, "disk": "/opt/volumes/docker 88.0%"})
		self.assertEqual(disk.cells("f2.frappe.cloud"), {"disk_0": 55.0, "disk": "/home/registry 70.0%"})

	def test_a_server_without_a_common_mountpoint_leaves_its_cell_blank(self):
		disk = self.disk_usage(
			{
				"f1.frappe.cloud": {"/data": 10.0},
				"f2.frappe.cloud": {"/data": 20.0},
				"r1.frappe.cloud": {"/": 30.0},
			}
		)

		self.assertEqual(disk.cells("r1.frappe.cloud"), {"disk_0": None, "disk": "/ 30.0%"})

	def test_boot_efi_column_comes_last_and_the_last_directory_is_bold(self):
		mounts = {"/": 40.0, "/boot/efi": 5.8, "/home/frappe/agent/.clones": 65.4}
		disk = self.disk_usage({"f1.frappe.cloud": mounts, "f2.frappe.cloud": mounts})

		self.assertEqual(
			[column["label"] for column in disk.columns()[:-1]],
			["Disk /<b></b> (%)", "Disk /home/frappe/agent/<b>.clones</b> (%)", "Disk /boot/<b>efi</b> (%)"],
		)
