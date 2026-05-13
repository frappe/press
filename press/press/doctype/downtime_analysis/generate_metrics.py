import datetime
import json
import os
import threading
import time

import requests

scrape_interval = 60  # seconds

# Configs
minimum_downtime_to_consider_as_complete_down_server = 1400 * scrape_interval  # 1440 * 60 = 24 hours
minimum_downtime_to_consider_in_top_k_down_servers_per_cluster = 10 * scrape_interval  # 10 * 60 = 10 minutes
minimum_downtime_to_consider_as_complete_down_site = 1400 * scrape_interval  # 1440 * 60 = 24 hours
minimum_downtime_to_consider_in_top_k_down_sites_per_cluster = 5 * scrape_interval  # 5 * 60 = 5 minutes
minimum_downtime_to_consider_in_top_k_servers_contributing_to_site_downtime_per_cluster = (
	5 * scrape_interval
)  # 5 * 60 = 5 minutes
top_k_sites_count = 40


def get_report_path(filename: str) -> str:
	import frappe

	path = os.path.join(
		frappe.utils.get_bench_path(),
		"sites",
		frappe.utils.get_site_path()[2:],
		"private",
		"files",
		"downtime_analysis_reports",
	)
	if not os.path.exists(path):
		os.makedirs(path)
	return os.path.join(path, filename)


def get_timerange_from_date(date_str: str) -> tuple:
	date_start = f"{date_str}T00:00:00+05:30"
	date_end = f"{date_str}T23:59:59+05:30"

	date_start_timestamp = int(datetime.datetime.fromisoformat(date_start).timestamp())
	date_end_timestamp = int(datetime.datetime.fromisoformat(date_end).timestamp())

	return date_start_timestamp, date_end_timestamp


def get_servers_downtime_data(
	cluster: str, date_str: str, prometheus_server: str, prometheus_auth: tuple
) -> dict:
	"""
	Response format:
	{
		"__total_downtime": total_downtime_of_all_servers_in_seconds,
		"<server>": downtime_in_seconds,
	}
	"""
	date_start, date_end = get_timerange_from_date(date_str)

	url = f'https://{prometheus_server}/prometheus/api/v1/query_range?query=sum(count_over_time(up{{job="node", cluster="{cluster}", instance!~"^t.*"}}[24h]  offset -24h)) by (instance) - sum(sum_over_time(up{{job="node", cluster="{cluster}", instance!~"^t.*"}}[24h]  offset -24h)) by (instance)&start={date_start}&end={date_end}&step=86400'
	response = requests.get(url, auth=prometheus_auth)
	response.raise_for_status()

	data = response.json()
	if data["status"] != "success":
		raise Exception("Failed to fetch data from Prometheus")

	result = {
		i.get("metric").get("instance"): int(i.get("values")[0][-1]) * scrape_interval
		for i in data.get("data", {}).get("result", [])
	}
	result["__total_downtime"] = sum(result.values())
	return result


def get_sites_downtime_data(
	cluster: str, date_str: str, prometheus_server: str, prometheus_auth: tuple
) -> dict:
	"""
	Response format:
	{
		"<server>": {
			"__total_downtime": total_downtime_of_all_sites_in_seconds,
			"<group>": {
				"__total_downtime": total_downtime_of_all_sites_in_seconds,
				"<site>": downtime_in_seconds,
			}
		}
	}
	"""
	date_start, date_end = get_timerange_from_date(date_str)
	url = f'https://{prometheus_server}/prometheus/api/v1/query_range?query=sum(count_over_time(probe_success{{job="site", cluster="{cluster}", server!~"^t.*"}}[24h]  offset -24h)) by (server, group, instance) - sum(sum_over_time(probe_success{{job="site", cluster="{cluster}", server!~"^t.*"}}[24h]  offset -24h)) by (server, group, instance)&start={date_start}&end={date_end}&step=86400'
	response = requests.get(url, auth=prometheus_auth)
	response.raise_for_status()

	data = response.json()
	if data["status"] != "success":
		raise Exception("Failed to fetch data from Prometheus")

	data = data.get("data", {}).get("result", [])

	result = {}
	for i in data:
		server = i.get("metric").get("server")
		group = i.get("metric").get("group")
		if server not in result:
			result[server] = {"__total_downtime": 0}
		if group not in result[server]:
			result[server][group] = {"__total_downtime": 0}

		downtime = int(i.get("values")[0][-1]) * scrape_interval
		result[server]["__total_downtime"] += downtime
		result[server][group]["__total_downtime"] += downtime
		result[server][group][i.get("metric").get("instance")] = downtime

	result["__total_downtime"] = sum(
		[result[server]["__total_downtime"] for server in result if server != "__total_downtime"]
	)

	return result


def get_server_downtime_data_for_date(
	clusters: str, date_str: str, prometheus_server: str, prometheus_auth: tuple
) -> dict:
	server_downtime = {}
	for cluster in clusters:
		done = False
		while not done:
			try:
				print(f"Fetching server data for {cluster} on {date_str}...")
				server_downtime[cluster] = get_servers_downtime_data(
					cluster, date_str, prometheus_server, prometheus_auth
				)
				done = True
			except Exception as e:
				print(f"Error fetching server data for {cluster} on {date_str}: {e}")
				print("Retrying...")
				time.sleep(5)

	server_downtime["__total_downtime"] = sum(
		[server_downtime[cluster]["__total_downtime"] for cluster in clusters]
	)
	return server_downtime


def get_site_downtime_data_for_date(
	clusters: str, date_str: str, prometheus_server: str, prometheus_auth: tuple
) -> dict:
	site_downtime = {}
	for cluster in clusters:
		done = False
		while not done:
			try:
				print(f"Fetching site data for {cluster} on {date_str}...")
				site_downtime[cluster] = get_sites_downtime_data(
					cluster, date_str, prometheus_server, prometheus_auth
				)
				done = True
			except Exception as e:
				print(f"Error fetching site data for {cluster} on {date_str}: {e}")
				print("Retrying...")
				time.sleep(5)

	site_downtime["__total_downtime"] = sum(
		[site_downtime[cluster]["__total_downtime"] for cluster in clusters]
	)
	return site_downtime


def get_data_for_all_clusters(
	start_date: str, end_date: str, clusters: list, prometheus_server: str, prometheus_auth: tuple
) -> dict:
	# Generate the list of last_n_days between start_date and end_date (inclusive)
	start = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
	end = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()
	days = (end - start).days + 1
	date_list = [(start + datetime.timedelta(days=i)).isoformat() for i in range(days)]

	server_downtime_file_name = get_report_path(f"server_downtime_data_{start_date}_to_{end_date}.json")
	site_downtime_file_name = get_report_path(f"site_downtime_data_{start_date}_to_{end_date}.json")

	if not os.path.exists(server_downtime_file_name):
		server_downtime = {}
		for date in date_list:
			server_downtime[date] = get_server_downtime_data_for_date(
				clusters, date, prometheus_server, prometheus_auth
			)

		with open(server_downtime_file_name, "w") as f:
			json.dump(server_downtime, f, indent=4)
		print(f"Server downtime data collected and saved to {server_downtime_file_name}.")
	else:
		print(f"{server_downtime_file_name} already exists. Skipping server data collection.")

	if not os.path.exists(site_downtime_file_name):
		site_downtime = {}
		for date in date_list:
			site_downtime[date] = get_site_downtime_data_for_date(
				clusters, date, prometheus_server, prometheus_auth
			)

		with open(site_downtime_file_name, "w") as f:
			json.dump(site_downtime, f, indent=4)
		print(f"Site downtime data collected and saved to {site_downtime_file_name}.")
	else:
		print(f"{site_downtime_file_name} already exists. Skipping site data collection.")

	return {
		"server_downtime": json.load(open(server_downtime_file_name, "r")),
		"site_downtime": json.load(open(site_downtime_file_name, "r")),
	}


def generate_server_downtime_report(  # noqa: C901
	start_date: str, end_date: str, server_downtime_data: dict, clusters: list
):
	report_data = {}  # store report data here

	file_name = get_report_path(f"server_downtime_report_{start_date}_to_{end_date}.json")
	if os.path.exists(file_name):
		print(f"{file_name} already exists. Skipping report generation.")
		return json.load(open(file_name, "r"))

	############# Prepare Some Common Data #############
	# Prepare total downtime of each cluster for the whole period
	cluster_total_downtime = {cluster: 0 for cluster in clusters}
	for _, clusters_data in server_downtime_data.items():
		for cluster in clusters:
			if cluster.startswith("__"):
				continue
			cluster_total_downtime[cluster] += clusters_data.get(cluster, {}).get("__total_downtime", 0)
	cluster_total_downtime["__total_downtime"] = sum(cluster_total_downtime.values())

	# Prepare total downtime of each server in each cluster for the whole period
	cluster_server_downtime = {cluster: {} for cluster in clusters}
	for _, clusters_data in server_downtime_data.items():
		for cluster in clusters:
			if cluster.startswith("__"):
				continue
			for server, downtime in clusters_data.get(cluster, {}).items():
				if server.startswith("__"):
					continue
				if server not in cluster_server_downtime[cluster]:
					cluster_server_downtime[cluster][server] = 0
				cluster_server_downtime[cluster][server] += downtime

	clusters_sorted_by_downtime = sorted(cluster_total_downtime.items(), key=lambda x: x[1], reverse=True)
	clusters_sorted_by_downtime = [i[0] for i in clusters_sorted_by_downtime if not i[0].startswith("__")]
	report_data["clusters_sorted_by_downtime"] = clusters_sorted_by_downtime
	############# Prepare Report #############

	# Servers with complete downtime (One Table with all the infos)
	servers_with_complete_downtime = []
	"""
	[
		{
			"dates": [date1, date2, ...],
			"server": server,
			"cluster": cluster,
			"total_downtime": total_downtime_in_seconds,
			"contribution_to_cluster_downtime": percentage,
			"contribution_to_total_downtime": percentage,
		}
	]
	"""

	for date, clusters_data in server_downtime_data.items():
		for cluster in clusters:
			if cluster.startswith("__"):
				continue
			for server, downtime in clusters_data.get(cluster, {}).items():
				if server.startswith("__"):
					continue
				if downtime >= minimum_downtime_to_consider_as_complete_down_server:
					entry = next(
						(
							item
							for item in servers_with_complete_downtime
							if item["server"] == server and item["cluster"] == cluster
						),
						None,
					)
					if entry:
						entry["dates"].append(date)
						entry["total_downtime"] += downtime
					else:
						servers_with_complete_downtime.append(
							{
								"cluster": cluster,
								"server": server,
								"dates": [date],
								"total_downtime": downtime,
							}
						)

	# Calculate contributions
	for entry in servers_with_complete_downtime:
		entry["contribution_to_cluster_downtime"] = round(
			entry["total_downtime"] / cluster_total_downtime[entry["cluster"]] * 100
			if cluster_total_downtime[entry["cluster"]] > 0
			else 0,
			2,
		)
		entry["contribution_to_total_downtime"] = round(
			entry["total_downtime"] / cluster_total_downtime["__total_downtime"] * 100
			if cluster_total_downtime["__total_downtime"] > 0
			else 0,
			2,
		)

	report_data["servers_with_complete_downtime"] = servers_with_complete_downtime

	# Find top 5 servers of each cluster with highest downtime
	# Use server_downtime_data to get the cluster of each server
	top_20_servers_with_highest_downtime_per_cluster = {}
	for cluster, servers in cluster_server_downtime.items():
		sorted_servers = sorted(servers.items(), key=lambda x: x[1], reverse=True)[:20]
		sorted_servers = [
			(server, downtime)
			for server, downtime in sorted_servers
			if downtime >= minimum_downtime_to_consider_in_top_k_down_servers_per_cluster
		]
		top_20_servers_with_highest_downtime_per_cluster[cluster] = [
			{"server": server, "total_downtime": downtime} for server, downtime in sorted_servers
		]

	report_data["top_20_servers_with_highest_downtime_per_cluster"] = (
		top_20_servers_with_highest_downtime_per_cluster
	)

	with open(file_name, "w") as f:
		json.dump(report_data, f, indent=4)
		print(f"Server uptime report generated and saved to {file_name}.")

	return report_data


def generate_site_downtime_report(start_date: str, end_date: str, site_downtime_data: dict, clusters: list):  # noqa: C901
	report_data = {}  # store report data here
	file_name = get_report_path(f"site_downtime_report_{start_date}_to_{end_date}.json")
	if os.path.exists(file_name):
		print(f"{file_name} already exists. Skipping report generation.")
		return json.load(open(file_name, "r"))

	############# Prepare Some Common Data #############
	# Prepare total downtime of each cluster for the whole period
	cluster_total_downtime = {cluster: 0 for cluster in clusters}
	for _, clusters_data in site_downtime_data.items():
		for cluster in clusters:
			if cluster.startswith("__"):
				continue
			cluster_total_downtime[cluster] += clusters_data.get(cluster, {}).get("__total_downtime", 0)
	cluster_total_downtime["__total_downtime"] = sum(cluster_total_downtime.values())

	# Sites with full downtime in any of the days (One Table with all the infos)
	sites_with_complete_downtime = []
	for date, clusters_data in site_downtime_data.items():
		"""
		[
			{
				"dates": [date1, date2, ...],
				"site": site,
				"server": server,
				"group": group,
				"cluster": cluster,
				"total_downtime": total_downtime_in_seconds,
				"contribution_to_server_downtime": percentage,
				"contribution_to_cluster_downtime": percentage,
				"contribution_to_total_downtime": percentage,
			}
		]
		"""
		for cluster in clusters:
			if cluster.startswith("__"):
				continue
			for server, groups in clusters_data.get(cluster, {}).items():
				if server.startswith("__"):
					continue
				for group, sites in groups.items():
					if group.startswith("__"):
						continue
					for site, downtime in sites.items():
						if site.startswith("__"):
							continue
						if downtime >= minimum_downtime_to_consider_as_complete_down_site:
							entry = next(
								(
									item
									for item in sites_with_complete_downtime
									if item["site"] == site
									and item["server"] == server
									and item["cluster"] == cluster
									and item["group"] == group
								),
								None,
							)
							if entry:
								entry["dates"].append(date)
								entry["total_downtime"] += downtime
							else:
								sites_with_complete_downtime.append(
									{
										"cluster": cluster,
										"server": server,
										"group": group,
										"site": site,
										"dates": [date],
										"total_downtime": downtime,
									}
								)
	# Calculate contributions
	for entry in sites_with_complete_downtime:
		# Contribution to server downtime
		server_downtime = 0
		for _, clusters_data in site_downtime_data.items():
			server_downtime += (
				clusters_data.get(entry["cluster"], {}).get(entry["server"], {}).get("__total_downtime", 0)
			)
		entry["contribution_to_server_downtime"] = round(
			entry["total_downtime"] / server_downtime * 100 if server_downtime > 0 else 0, 2
		)

		# Contribution to cluster downtime
		entry["contribution_to_cluster_downtime"] = round(
			entry["total_downtime"] / cluster_total_downtime[entry["cluster"]] * 100
			if cluster_total_downtime[entry["cluster"]] > 0
			else 0,
			2,
		)
		# Contribution to total downtime
		entry["contribution_to_total_downtime"] = round(
			entry["total_downtime"] / cluster_total_downtime["__total_downtime"] * 100
			if cluster_total_downtime["__total_downtime"] > 0
			else 0,
			2,
		)

	report_data["sites_with_complete_downtime"] = sites_with_complete_downtime

	# Top 40 sites with highest downtime in each cluster
	# Use site_downtime_data to get the cluster of each server
	top_k_sites_with_highest_downtime_per_cluster = {}
	for cluster in clusters:
		if cluster.startswith("__"):
			continue
		site_info = {}
		for _, clusters_data in site_downtime_data.items():
			for server, groups in clusters_data.get(cluster, {}).items():
				if server.startswith("__"):
					continue
				for group, sites in groups.items():
					if group.startswith("__"):
						continue
					for site, downtime in sites.items():
						if site.startswith("__"):
							continue
						key = (site, server, group)
						if key not in site_info:
							site_info[key] = 0
						site_info[key] += downtime

		# Sort by downtime and filter
		sorted_sites = sorted(site_info.items(), key=lambda x: x[1], reverse=True)[:top_k_sites_count]
		sorted_sites = [
			(site_tuple, downtime)
			for site_tuple, downtime in sorted_sites
			if downtime >= minimum_downtime_to_consider_in_top_k_down_sites_per_cluster
		]
		top_k_sites_with_highest_downtime_per_cluster[cluster] = [
			{"site": site, "server": server, "bench": group, "total_downtime": downtime}
			for (site, server, group), downtime in sorted_sites
		]
	report_data["top_k_sites_with_highest_downtime_per_cluster"] = (
		top_k_sites_with_highest_downtime_per_cluster
	)

	# Top 20 servers of each cluster with highest site downtime
	top_20_servers_with_highest_site_downtime_per_cluster = {}
	for cluster in clusters:
		if cluster.startswith("__"):
			continue
		server_site_downtime = {}
		for _, clusters_data in site_downtime_data.items():
			for server, groups in clusters_data.get(cluster, {}).items():
				if server.startswith("__"):
					continue
				if server not in server_site_downtime:
					server_site_downtime[server] = 0
				for group, sites in groups.items():
					if group.startswith("__"):
						continue
					for site, downtime in sites.items():
						if site.startswith("__"):
							continue
						server_site_downtime[server] += downtime

		sorted_servers = sorted(server_site_downtime.items(), key=lambda x: x[1], reverse=True)[:20]
		sorted_servers = [
			(server, downtime)
			for server, downtime in sorted_servers
			if downtime
			>= minimum_downtime_to_consider_in_top_k_servers_contributing_to_site_downtime_per_cluster
		]
		top_20_servers_with_highest_site_downtime_per_cluster[cluster] = [
			{"server": server, "total_downtime": downtime} for server, downtime in sorted_servers
		]

	report_data["top_20_servers_with_highest_site_downtime_per_cluster"] = (
		top_20_servers_with_highest_site_downtime_per_cluster
	)

	# List out the probematic sites found in reports for further investigation
	problematic_sites = []
	for entry in sites_with_complete_downtime:
		problematic_sites.append(entry["site"])
	for _, sites in top_k_sites_with_highest_downtime_per_cluster.items():
		for site_entry in sites:
			if site_entry["site"] not in problematic_sites:
				problematic_sites.append(site_entry["site"])

	report_data["problematic_sites"] = problematic_sites

	# Analyze those sites for further issues
	report_data["problematic_sites_analysis_report"] = analyze_sites_in_thread(problematic_sites)

	with open(file_name, "w") as f:
		json.dump(report_data, f, indent=4)
		print(f"Site uptime report generated and saved to {file_name}.")

	return report_data


def analyze_sites_in_thread(sites: list, batch_size: int = 50) -> dict:
	results = {}
	threads: list[threading.Thread] = []
	for i in range(0, len(sites), batch_size):
		batch = sites[i : i + batch_size]
		thread = threading.Thread(target=lambda b: results.update(analyze_sites(b)), args=(batch,))
		threads.append(thread)
		thread.start()

	for thread in threads:
		thread.join()

	return results


def analyze_sites(sites: list):
	results = {}
	status_code_map = {
		200: "reachable",
		401: "unauthorized",
		402: "site_suspended",
		403: "forbidden",
		404: "site_not_found",
		429: "rate_limited",
		500: "internal_server_error",
		502: "bad_gateway",
		503: "site_in_maintenance",
	}
	for site in sites:
		results[site] = {
			"status": "reachable",  # reachable, timeout, error, redirect_external
			"status_code": 0,
			"redirects": [],
			"error": "",
			"proxy_server": "",  # Frappe Cloud, cloudflare
		}
		try:
			# Check if sites are reachable
			try:
				# If there are redirects, follow it and log those
				done = False
				url = f"https://{site}/api/method/ping"
				while not done:
					response = requests.get(url, timeout=(2, 10), allow_redirects=False)
					# Record status code
					results[site]["status_code"] = response.status_code
					# Check if we are getting redirected to some other server in /api/method/ping check
					results[site]["proxy_server"] = response.headers.get(
						"Server", ""
					) or response.headers.get("server", "")
					if response.status_code in [301, 302]:
						# Record redirects
						url = response.headers.get("Location")
						results[site]["redirects"].append(url)
					elif response.status_code in status_code_map:
						results[site]["status"] = status_code_map.get(response.status_code, "unreachable")
						done = True
					else:
						done = True

				if results[site]["proxy_server"] and results[site]["proxy_server"].lower() != "frappe cloud":
					results[site]["status"] = "redirect_external"

			except requests.Timeout:
				results[site]["status"] = "timeout"

			# In that case, check dns record of the custom domain
			# Finally add a message regarding possible issues with the site

		except Exception as e:
			results[site]["status"] = "error"
			results[site]["error"] = str(e)
			continue

	return results


def is_report_available(start_date: str, end_date: str):
	files = [
		get_report_path(f"server_downtime_report_{start_date}_to_{end_date}.json"),
		get_report_path(f"site_downtime_report_{start_date}_to_{end_date}.json"),
	]
	if all([os.path.exists(f) for f in files]):
		return True
	return False
