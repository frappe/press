from __future__ import annotations

from typing import Any


def generate_report(payload: dict[str, Any]) -> dict[str, Any]:
	evidence: list[str] = []
	timeline: list[dict[str, Any]] = []
	causes: list[str] = []
	next_steps: list[str] = []
	confidence = "Low"

	site = payload.get("site") or {}
	bench = payload.get("bench") or {}
	deployments = payload.get("deployments") or []
	jobs = payload.get("background_jobs") or {}
	backups = payload.get("backups") or {}
	domains = payload.get("domains") or {}
	incidents = payload.get("incidents") or []
	errors = payload.get("errors") or {}
	app_server_metrics = payload.get("app_server_metrics") or {}
	db_server_metrics = payload.get("db_server_metrics") or {}
	server_advanced_analytics = payload.get("server_advanced_analytics") or {}
	bench_processes = payload.get("bench_processes") or {}
	site_uptime = payload.get("site_uptime") or {}
	site_performance = payload.get("site_performance") or {}
	slow_queries = payload.get("slow_queries") or {}
	database_processes = payload.get("database_processes") or {}
	slow_query_share = payload.get("database_slow_query_share") or {}
	request_share = payload.get("app_server_request_share") or {}
	web_error_log = payload.get("web_error_log") or {}

	_add_site_evidence(site, evidence, causes, next_steps)
	_add_bench_evidence(bench, evidence, causes, next_steps)
	_add_deployment_evidence(deployments, evidence, timeline, causes, next_steps)
	_add_job_evidence(jobs, errors, evidence, timeline, causes, next_steps)
	_add_backup_evidence(backups, evidence, timeline, next_steps)
	_add_domain_evidence(domains, evidence, causes, next_steps)
	_add_incident_evidence(incidents, evidence, timeline, causes, next_steps)
	_add_bench_process_evidence(bench_processes, evidence, causes, next_steps)
	_add_uptime_evidence(site_uptime, evidence, causes, next_steps)
	_add_server_metrics_evidence(
		app_server_metrics,
		db_server_metrics,
		server_advanced_analytics,
		slow_queries,
		evidence,
		causes,
		next_steps,
	)
	_add_performance_evidence(site_performance, evidence, causes, next_steps)
	_add_slow_query_evidence(slow_queries, evidence, causes, next_steps)
	_add_database_process_evidence(database_processes, evidence, causes, next_steps)
	_add_slow_query_share_evidence(slow_query_share, evidence, causes, next_steps)
	_add_request_share_evidence(request_share, app_server_metrics, evidence, causes, next_steps)
	_add_web_error_evidence(web_error_log, evidence, causes, next_steps)

	if causes:
		confidence = "High" if _has_blocking_signal(site, bench, deployments, incidents) else "Medium"
	else:
		causes.append("No obvious platform-side issue found from the read-only checks.")
		next_steps.append(
			"Review customer-provided symptoms and rerun investigation after reproducing the issue."
		)

	return {
		"summary": _summary(site, causes, evidence),
		"likely_cause": causes[0],
		"recommended_next_steps": _unique(next_steps),
		"confidence": confidence,
		"evidence": evidence,
		"timeline": timeline,
	}


def _add_site_evidence(site, evidence, causes, next_steps):
	status = site.get("status")
	if status != "Active":
		evidence.append(f"Site status is {status}.")
		causes.append(f"Site is not Active; current lifecycle state is {status}.")
		next_steps.append("Check the latest site lifecycle action before attempting operational remediation.")

	if site.get("archive_failed"):
		evidence.append("Site has archive_failed set.")
		causes.append("A previous archive operation failed for this site.")

	if site.get("monitoring_disabled"):
		evidence.append("Site monitoring is disabled.")
		next_steps.append("Re-enable or verify monitoring before relying on absence of alerts.")

	usage = site.get("usage_percent") or {}
	for resource in ("disk", "database", "cpu"):
		value = usage.get(resource) or 0
		if value >= 120:
			evidence.append(f"{resource.title()} usage is {value}%.")
			causes.append(f"{resource.title()} usage is critically over quota.")
			next_steps.append(f"Reduce {resource} usage or move the site to a plan with more capacity.")
		elif value >= 90:
			evidence.append(f"{resource.title()} usage is high at {value}%.")


def _add_bench_evidence(bench, evidence, causes, next_steps):
	if not bench:
		evidence.append("No bench metadata found for the site.")
		return

	if bench.get("status") != "Active":
		evidence.append(f"Bench status is {bench.get('status')}.")
		causes.append(f"Bench is not Active; current state is {bench.get('status')}.")
		next_steps.append("Check bench deployment or recovery state before restarting services.")

	if bench.get("last_inplace_update_failed"):
		evidence.append("Last in-place bench update failed.")
		causes.append("The bench has a failed in-place update marker.")

	if bench.get("resetting_bench"):
		evidence.append("Bench reset is currently in progress.")


def _add_bench_process_evidence(processes, evidence, causes, next_steps):
	if not processes.get("available"):
		return

	stopped = processes.get("stopped_processes") or []
	if not stopped:
		return

	web_stopped = [p for p in stopped if "web" in p.get("name", "")]
	if web_stopped:
		name = web_stopped[0]["name"]
		status = web_stopped[0]["status"]
		evidence.append(f"Gunicorn web process '{name}' is {status}.")
		causes.append("Gunicorn web workers are not running — direct cause of 502 errors.")
		next_steps.append(
			"Check web.error.log and recent deployments for the crash reason before restarting."
		)
		return

	worker_stopped = [p for p in stopped if "worker" in p.get("name", "")]
	if worker_stopped:
		evidence.append(f"{len(worker_stopped)} background worker process(es) are not running.")


def _add_uptime_evidence(site_uptime, evidence, causes, next_steps):
	if not site_uptime.get("available"):
		return

	up = site_uptime.get("up")
	http_status = site_uptime.get("http_status_code")

	if up is False:
		code_note = f" (HTTP {http_status})" if http_status else ""
		evidence.append(f"Site probe is currently DOWN{code_note}.")
		causes.append(f"Probe check reports the site is unreachable{code_note} — not a client-side issue.")
		next_steps.append("Confirm with a second probe or browser check before escalating to infrastructure.")
	elif http_status and http_status >= 500:
		evidence.append(f"Site probe is responding with HTTP {http_status}.")
		causes.append(f"Site is returning HTTP {http_status} to external probes.")


def _add_deployment_evidence(deployments, evidence, timeline, causes, next_steps):
	for deployment in deployments:
		timeline.append(
			{
				"type": "site_update",
				"name": deployment.get("name"),
				"status": deployment.get("status"),
				"when": deployment.get("update_start")
				or deployment.get("scheduled_time")
				or deployment.get("creation"),
				"deploy_type": deployment.get("deploy_type"),
			}
		)

	latest = deployments[0] if deployments else None
	if not latest:
		return

	if latest.get("status") == "Fatal":
		evidence.append("Latest site update ended with Fatal.")
		causes.append("Recent site update failed permanently; recovery was not successful.")
		next_steps.append(
			"Open the latest Site Update and inspect the linked Agent Job status before retrying."
		)
	elif latest.get("status") == "Cancelled":
		evidence.append("Latest site update was cancelled.")
		causes.append("Recent site update was cancelled.")
		next_steps.append(
			"Open the latest Site Update and inspect the linked Agent Job status before retrying."
		)
	elif latest.get("status") == "Failure":
		evidence.append("Latest site update is in Failure state; a recovery job is likely being created.")
		causes.append("Recent site update hit a failure; recovery is in progress or pending.")
		next_steps.append("Wait briefly for the recovery job to be created, then check its status.")
	elif latest.get("status") == "Recovered":
		evidence.append(
			"Latest site update ended with Recovered — it failed but was rolled back successfully."
		)
	elif latest.get("status") in {"Pending", "Running", "Recovering", "Scheduled"}:
		evidence.append(f"Latest site update is {latest.get('status')}.")
		causes.append("A site update is currently in progress.")
		next_steps.append(
			"Wait for the site update to finish or investigate the linked running job if it is stuck."
		)


def _add_job_evidence(jobs, errors, evidence, timeline, causes, next_steps):
	for job in jobs.get("recent") or []:
		timeline.append(
			{
				"type": "agent_job",
				"name": job.get("name"),
				"status": job.get("status"),
				"when": job.get("start") or job.get("creation"),
				"job_type": job.get("job_type"),
			}
		)

	# Failed agent jobs are recorded as evidence but never as a cause — a job fails
	# because of something else (bench down, disk full, bad deploy), so treating it
	# as the cause just restates the symptom.
	failed_count = errors.get("failed_job_count") or 0
	if failed_count:
		evidence.append(
			f"{failed_count} agent jobs failed in the last {errors.get('window_hours')} hours "
			"(symptom — look for the underlying cause)."
		)

	running_count = (jobs.get("counts_by_status") or {}).get("Running", 0)
	if running_count:
		evidence.append(f"{running_count} agent jobs are currently marked Running in the recent window.")


def _add_backup_evidence(backups, evidence, timeline, next_steps):
	for backup in backups.get("recent") or []:
		timeline.append(
			{
				"type": "site_backup",
				"name": backup.get("name"),
				"status": backup.get("status"),
				"when": backup.get("creation"),
				"physical": bool(backup.get("physical")),
			}
		)

	latest = backups.get("latest")
	if latest and latest.get("status") == "Failure":
		evidence.append("Latest site backup failed.")
		next_steps.append("Check backup health before destructive maintenance or restore operations.")


def _add_domain_evidence(domains, evidence, causes, next_steps):
	counts = domains.get("counts_by_status") or {}
	broken = counts.get("Broken", 0)
	if broken:
		evidence.append(f"{broken} site domains are Broken.")
		causes.append("One or more site domains have DNS/TLS issues.")
		next_steps.append(
			"Check Site Domain records for DNS and TLS status without exposing domain names in the agent report."
		)


def _add_incident_evidence(incidents, evidence, timeline, causes, next_steps):
	if not incidents:
		return

	evidence.append(f"{len(incidents)} active platform incidents match the site server or cluster.")
	causes.append("An active platform incident may be affecting this site.")
	next_steps.append(
		"Correlate user impact with the matching Incident records before site-specific remediation."
	)
	for incident in incidents:
		timeline.append(
			{
				"type": "incident",
				"name": incident.get("name"),
				"status": incident.get("status"),
				"when": incident.get("creation"),
				"incident_type": incident.get("type"),
			}
		)


def _summary(site, causes, evidence):
	if evidence:
		return f"Investigation for {site.get('name')} found {len(evidence)} signal(s). {causes[0]}"
	return f"Investigation for {site.get('name')} found no obvious platform-side issue."


def _has_blocking_signal(site, bench, deployments, incidents):
	return bool(
		site.get("status") != "Active"
		or bench.get("status") not in {None, "Active"}
		or (deployments and deployments[0].get("status") in {"Fatal", "Cancelled"})
		or incidents
	)


def _add_server_metrics_evidence(
	app_metrics, db_metrics, advanced_analytics, slow_queries, evidence, causes, next_steps
):
	_add_app_server_evidence(app_metrics, advanced_analytics, evidence, causes, next_steps)
	_add_db_server_evidence(db_metrics, slow_queries, evidence, causes, next_steps)


def _add_app_server_evidence(app_metrics, advanced_analytics, evidence, causes, next_steps):
	if not app_metrics.get("available"):
		return

	cpu = app_metrics.get("cpu") or {}
	if cpu.get("spike_detected"):
		evidence.append(
			f"App server CPU peaked at {cpu['peak']}% (mean {cpu['mean']}%) in the investigation window."
		)
		causes.append(
			"App server CPU spiked. Bench containers on shared servers have no CPU limits; "
			"another tenant may be responsible."
		)
		next_steps.append(
			"Check server advanced analytics to identify whether another tenant caused the spike. "
			"If the site's own share is small, the issue is likely a noisy neighbor."
		)

	if advanced_analytics.get("available"):
		rank = advanced_analytics.get("target_site_rank")
		share = advanced_analytics.get("target_site_share_percent")
		count = advanced_analytics.get("site_count")
		if rank and share is not None:
			evidence.append(
				f"Site ranks #{rank} of {count} tenants by CPU usage on the app server "
				f"({share}% of server total)."
			)


def _add_db_server_evidence(db_metrics, slow_queries, evidence, causes, next_steps):
	if not db_metrics.get("available"):
		return

	db_cpu = db_metrics.get("cpu") or {}
	db_iops = db_metrics.get("iops") or {}

	if db_cpu.get("spike_detected"):
		evidence.append(
			f"Database server CPU peaked at {db_cpu['peak']}% (mean {db_cpu['mean']}%) in the investigation window."
		)
		causes.append(
			"Database server CPU spiked. Shared database servers have no container-level isolation; "
			"there is no automatic fix."
		)
		_add_busy_db_cpu_query_shape(slow_queries, evidence, next_steps)
		next_steps.append(
			"Use database server advanced analytics to identify the tenant driving CPU. "
			"Remediation requires manually moving the site or the heavy tenant to a dedicated server."
		)

	if db_iops.get("spike_detected"):
		evidence.append(
			f"Database server disk I/O peaked at {db_iops['peak']} IOPS "
			f"(mean {db_iops['mean']}) in the investigation window."
		)
		if not db_cpu.get("spike_detected"):
			causes.append("Database server disk I/O spiked.")
			next_steps.append(
				"Check database server advanced analytics to identify which tenant is driving heavy disk I/O."
			)


_HEAVY_QUERY_AVG_S = 1.0  # a query averaging this long is heavy by itself, not merely frequent


def _add_busy_db_cpu_query_shape(slow_queries, evidence, next_steps):
	"""
	Busy database CPU comes from either too many queries or a few too-slow ones.

	It is the latter most of the time, so point the support agent at the slow
	queries before they go looking for a noisy neighbor.
	"""
	top = slow_queries.get("top_queries") or []
	if not slow_queries.get("available") or not top:
		next_steps.append(
			"Check the site's slow queries — busy database CPU is usually a few too-slow queries."
		)
		return

	worst = top[0]
	if worst["avg_duration_s"] >= _HEAVY_QUERY_AVG_S:
		evidence.append(
			f"Database CPU is busy and the slowest query averages {worst['avg_duration_s']}s — "
			"a few too-slow queries rather than query volume."
		)
	else:
		evidence.append(
			f"Database CPU is busy and the slowest query ran {worst['count']} times averaging only "
			f"{worst['avg_duration_s']}s — query volume rather than a few too-slow queries."
		)


def _add_performance_evidence(performance, evidence, causes, next_steps):
	if not performance.get("available"):
		return

	endpoints = performance.get("top_slow_endpoints") or []
	if not endpoints:
		return

	slow = [e for e in endpoints if e.get("avg_duration_s", 0) >= 1.0]
	spiky = [e for e in endpoints if e.get("spike_detected")]

	if not slow and not spiky:
		return

	_add_slow_endpoint_evidence(slow, evidence, causes, next_steps)
	_add_spiky_endpoint_evidence(spiky, evidence, next_steps)


def _add_slow_endpoint_evidence(slow, evidence, causes, next_steps):
	if not slow:
		return

	slowest = slow[0]
	evidence.append(
		f"Slowest endpoint '{slowest['path']}' averaged {slowest['avg_duration_s']}s per request "
		f"in the investigation window (peak {slowest['peak_duration_s']}s)."
	)

	custom = [e for e in slow if e.get("is_custom")]
	if custom:
		custom_paths = ", ".join(f"'{e['path']}'" for e in custom[:2])
		evidence.append(f"Slow endpoints from non-Frappe apps: {custom_paths}.")
		causes.append(
			"Custom app endpoints are slow; the cause is likely application-level, not infrastructure."
		)
	else:
		causes.append("Slow endpoint requests are consuming web workers and may be causing 504 errors.")

	next_steps.append(
		"Use Frappe Recorder on the site to profile the slow endpoint. "
		"Disable Recorder immediately after profiling to avoid further degradation."
	)

	if len(slow) > 1:
		others = ", ".join(f"'{e['path']}'" for e in slow[1:3])
		evidence.append(f"Other slow endpoints in the investigation window: {others}.")


def _add_spiky_endpoint_evidence(spiky, evidence, next_steps):
	if not spiky:
		return

	for endpoint in spiky[:2]:
		evidence.append(
			f"Endpoint '{endpoint['path']}' shows intermittent spikes: "
			f"peak {endpoint['peak_duration_s']}s vs mean {endpoint['avg_duration_s']}s."
		)
	next_steps.append(
		"Spiky endpoints suggest a specific document type or operation triggers the slowness. "
		"Use Frappe Recorder to capture the slow request in context."
	)


_SLOW_QUERY_TOTAL_DURATION_S = 10.0  # DB time a query family must burn in 24h to be a cause
_FULL_SCAN_ROW_RATIO = 100  # rows examined per row sent above which an index is likely missing


def _add_slow_query_evidence(slow_queries, evidence, causes, next_steps):
	top = slow_queries.get("top_queries") or []
	if not slow_queries.get("available") or not top:
		return

	worst = top[0]
	evidence.append(
		f"Slowest database query ran {worst['count']} time(s) in the investigation window, "
		f"{worst['total_duration_s']}s total ({worst['avg_duration_s']}s average): {worst['query']}"
	)

	if _scans_too_many_rows(worst):
		evidence.append(
			f"It examined {worst['rows_examined']} rows to return {worst['rows_sent']} — likely a missing index."
		)
		causes.append("A slow database query is scanning far more rows than it returns; an index is missing.")
		next_steps.append(
			"Run the MariaDB Slow Queries report for the site and add an index for the scanned column."
		)
	elif worst["total_duration_s"] >= _SLOW_QUERY_TOTAL_DURATION_S:
		causes.append("Slow database queries are consuming significant database time for this site.")
		next_steps.append(
			"Run the MariaDB Slow Queries report for the site to see the full query list with examples."
		)


_QUERY_SNIPPET_CHARS = 200  # keep evidence readable; the full query is in the payload
_VERY_HIGH_CPU_PERCENT = 90.0  # below this the app server still had headroom for every bench
_NOISY_NEIGHBOR_CAUSE = "Another tenant on the shared database server is driving the load, not this site."
_NOISY_NEIGHBOR_NEXT_STEP = (
	"Move the heavy tenant or this site to a dedicated database server — shared database "
	"servers have no isolation and there is no automatic fix."
)


def _add_database_process_evidence(database_processes, evidence, causes, next_steps):
	processes = database_processes.get("processes") or []
	if not database_processes.get("available") or not processes:
		return

	_add_longest_connection_evidence(database_processes, evidence, next_steps)
	_add_noisy_neighbor_evidence(database_processes, evidence, causes, next_steps)


def _add_noisy_neighbor_evidence(database_processes, evidence, causes, next_steps):
	"""The processlist is what settles whether the site is the culprit or the victim."""
	total = database_processes["count"]
	target = database_processes.get("target_site_connections") or 0

	if database_processes.get("busiest_site_is_target"):
		evidence.append(
			f"The site holds {target} of {total} database connections — the load is its own, "
			"not a noisy neighbor."
		)
		return

	busiest = database_processes.get("busiest_site_connections") or 0
	evidence.append(
		f"Another site on the database server holds {busiest} of {total} connections against this "
		f"site's {target} — noisy neighbor confirmed."
	)
	causes.append(_NOISY_NEIGHBOR_CAUSE)
	next_steps.append(_NOISY_NEIGHBOR_NEXT_STEP)


def _add_request_share_evidence(share, app_metrics, evidence, causes, next_steps):
	"""
	The same question on the app server: is this site's own traffic the load?

	A busy neighbor only hurts if it is on this site's bench, where the two share
	gunicorn workers, or if the server's CPU was high enough that there was nothing
	left to go around.
	"""
	if not share.get("available"):
		return

	target = share.get("target_site_share_percent")
	if share.get("busiest_site_is_target"):
		evidence.append(
			f"This site accounts for {target}% of request time on the app server — "
			"the load is its own, not a noisy neighbor."
		)
		return

	busiest = share["busiest_site_share_percent"]
	if share.get("busiest_site_shares_bench"):
		evidence.append(
			f"Another site on the same bench accounts for {busiest}% of request time on the app "
			f"server against this site's {target}%."
		)
		causes.append("Another site on the same bench is consuming the gunicorn workers this site shares.")
		next_steps.append(
			"Move one of the two sites to its own bench — sites on a bench share gunicorn workers."
		)
		return

	peak = (app_metrics.get("cpu") or {}).get("peak") or 0
	if peak < _VERY_HIGH_CPU_PERCENT:
		evidence.append(
			f"Another site on the app server accounts for {busiest}% of request time against this "
			f"site's {target}%, but the server only peaked at {peak}% CPU on a different bench — "
			"it had headroom, so this is not a noisy neighbor."
		)
		return

	evidence.append(
		f"Another site on the app server accounts for {busiest}% of request time against this "
		f"site's {target}%, with the server at {peak}% CPU — noisy neighbor confirmed."
	)
	causes.append("Another tenant on the shared app server is consuming the CPU, not this site.")
	next_steps.append(
		"Bench containers on shared app servers have no CPU limits — move the heavy tenant or "
		"this site to another server."
	)


def _add_slow_query_share_evidence(share, evidence, causes, next_steps):
	"""What the processlist does for a live problem, the slow log does for a past one."""
	if not share.get("available"):
		return

	target = share.get("target_site_share_percent")
	if share.get("busiest_site_is_target"):
		evidence.append(
			f"This site accounts for {target}% of slow-query time on the database server — "
			"the load is its own, not a noisy neighbor."
		)
		return

	evidence.append(
		f"Another site accounts for {share['busiest_site_share_percent']}% of slow-query time on the "
		f"database server against this site's {target}% — noisy neighbor confirmed."
	)
	causes.append(_NOISY_NEIGHBOR_CAUSE)
	next_steps.append(_NOISY_NEIGHBOR_NEXT_STEP)


def _add_longest_connection_evidence(database_processes, evidence, next_steps):
	longest = database_processes["processes"][0]
	evidence.append(
		f"{database_processes['count']} database connections are open right now; the longest has run "
		f"for {longest['seconds']}s in state '{longest['state']}': "
		f"{longest['query'][:_QUERY_SNIPPET_CHARS]}"
	)
	next_steps.append(
		"Read the live processlist in this investigation's payload to see what the database is "
		"busy with before killing or optimizing anything."
	)


def _scans_too_many_rows(query):
	return query["rows_sent"] > 0 and query["rows_examined"] >= query["rows_sent"] * _FULL_SCAN_ROW_RATIO


def _add_web_error_evidence(web_error_log, evidence, causes, next_steps):
	if not web_error_log.get("available"):
		return

	count = web_error_log.get("error_count") or 0
	if not count:
		return

	recent = web_error_log.get("recent_errors") or []
	evidence.append(f"{count} ERROR/CRITICAL entries in web.error.log (last {len(recent)} collected).")
	_classify_web_errors(recent, causes, next_steps)


def _classify_web_errors(recent, causes, next_steps):
	if _has_db_connectivity_error(recent):
		causes.append(
			"Web error log shows database connectivity failures — the app server cannot reach the database."
		)
		next_steps.append(
			"Check database server status and network connectivity between the app server and database server."
		)
		return

	if _has_import_error(recent):
		causes.append(
			"Web error log shows module import errors — the application may be in a broken state after a deployment."
		)
		next_steps.append(
			"Check recent deployments; a partially applied update may have left the app in a broken state."
		)
		return

	if _has_worker_crash(recent):
		causes.append("Web error log shows CRITICAL entries — web workers crashed or timed out.")
		next_steps.append(
			"Review the web_error_log entries in this investigation's payload for the crash context."
		)
		return

	latest = next(
		(entry.get("exception") or entry.get("description") for entry in reversed(recent) if entry),
		None,
	)
	if latest:
		causes.append(f"Web error log shows application exceptions: {latest}")
	next_steps.append(
		"Review the web_error_log entries in this investigation's payload for exception details."
	)


def _has_db_connectivity_error(recent):
	return any(
		"can't connect" in (entry.get("exception") or entry.get("description") or "").lower()
		or "operationalerror" in (entry.get("exception") or entry.get("description") or "").lower()
		for entry in recent
	)


def _has_import_error(recent):
	return any(
		"importerror" in (entry.get("exception") or entry.get("description") or "").lower()
		or "modulenotfounderror" in (entry.get("exception") or entry.get("description") or "").lower()
		for entry in recent
	)


def _has_worker_crash(recent):
	return any("critical" in entry.get("level", "") for entry in recent)


def _unique(values):
	unique_values = []
	for value in values:
		if value not in unique_values:
			unique_values.append(value)
	return unique_values
