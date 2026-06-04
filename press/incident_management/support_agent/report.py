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
	site_performance = payload.get("site_performance") or {}

	_add_site_evidence(site, evidence, causes, next_steps)
	_add_bench_evidence(bench, evidence, causes, next_steps)
	_add_deployment_evidence(deployments, evidence, timeline, causes, next_steps)
	_add_job_evidence(jobs, errors, evidence, timeline, causes, next_steps)
	_add_backup_evidence(backups, evidence, timeline, next_steps)
	_add_domain_evidence(domains, evidence, causes, next_steps)
	_add_incident_evidence(incidents, evidence, timeline, causes, next_steps)
	_add_server_metrics_evidence(
		app_server_metrics, db_server_metrics, server_advanced_analytics, evidence, causes, next_steps
	)
	_add_performance_evidence(site_performance, evidence, causes, next_steps)

	if causes:
		confidence = "High" if _has_blocking_signal(site, bench, deployments, errors, incidents) else "Medium"
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

	failed_count = errors.get("failed_job_count") or 0
	if failed_count:
		evidence.append(f"{failed_count} agent jobs failed in the last {errors.get('window_hours')} hours.")
		causes.append("Recent platform agent jobs are failing for this site.")
		next_steps.append(
			"Inspect the failed Agent Job records and retry only after confirming the failure is transient."
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


def _has_blocking_signal(site, bench, deployments, errors, incidents):
	return bool(
		site.get("status") != "Active"
		or bench.get("status") not in {None, "Active"}
		or (deployments and deployments[0].get("status") in {"Fatal", "Cancelled"})
		or errors.get("failed_job_count")
		or incidents
	)


def _add_server_metrics_evidence(app_metrics, db_metrics, advanced_analytics, evidence, causes, next_steps):
	_add_app_server_evidence(app_metrics, advanced_analytics, evidence, causes, next_steps)
	_add_db_server_evidence(db_metrics, evidence, causes, next_steps)


def _add_app_server_evidence(app_metrics, advanced_analytics, evidence, causes, next_steps):
	if not app_metrics.get("available"):
		return

	cpu = app_metrics.get("cpu") or {}
	if cpu.get("spike_detected"):
		evidence.append(
			f"App server CPU peaked at {cpu['peak']}% (mean {cpu['mean']}%) over the last 24 hours."
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


def _add_db_server_evidence(db_metrics, evidence, causes, next_steps):
	if not db_metrics.get("available"):
		return

	db_cpu = db_metrics.get("cpu") or {}
	db_iops = db_metrics.get("iops") or {}

	if db_cpu.get("spike_detected"):
		evidence.append(
			f"Database server CPU peaked at {db_cpu['peak']}% (mean {db_cpu['mean']}%) over the last 24 hours."
		)
		causes.append(
			"Database server CPU spiked. Shared database servers have no container-level isolation; "
			"there is no automatic fix."
		)
		next_steps.append(
			"Use database server advanced analytics to identify the tenant driving CPU. "
			"Remediation requires manually moving the site or the heavy tenant to a dedicated server."
		)

	if db_iops.get("spike_detected"):
		evidence.append(
			f"Database server disk I/O peaked at {db_iops['peak']} IOPS "
			f"(mean {db_iops['mean']}) over the last 24 hours."
		)
		if not db_cpu.get("spike_detected"):
			causes.append("Database server disk I/O spiked.")
			next_steps.append(
				"Check database server advanced analytics to identify which tenant is driving heavy disk I/O."
			)


def _add_performance_evidence(performance, evidence, causes, next_steps):
	if not performance.get("available"):
		return

	endpoints = performance.get("top_slow_endpoints") or []
	if not endpoints:
		return

	slowest = endpoints[0]
	avg = slowest.get("avg_duration_s", 0)
	if avg < 1.0:
		return

	evidence.append(
		f"Slowest endpoint '{slowest['path']}' averaged {avg}s per request over the last 24 hours "
		f"(peak {slowest.get('peak_duration_s')}s)."
	)
	causes.append("Slow endpoint requests are consuming web workers and may be causing 504 errors.")
	next_steps.append(
		"Use Frappe Recorder on the site to profile the slow endpoint. "
		"Disable Recorder immediately after profiling to avoid further degradation."
	)
	if len(endpoints) > 1:
		others = ", ".join(f"'{e['path']}'" for e in endpoints[1:3])
		evidence.append(f"Other slow endpoints in the last 24 hours: {others}.")


def _unique(values):
	unique_values = []
	for value in values:
		if value not in unique_values:
			unique_values.append(value)
	return unique_values
