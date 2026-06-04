from __future__ import annotations

from typing import Any


def generate_report(payload: dict[str, Any]) -> dict[str, Any]:
	evidence = []
	timeline = []
	causes = []
	next_steps = []
	confidence = "Low"

	site = payload.get("site") or {}
	bench = payload.get("bench") or {}
	deployments = payload.get("deployments") or []
	jobs = payload.get("background_jobs") or {}
	backups = payload.get("backups") or {}
	domains = payload.get("domains") or {}
	incidents = payload.get("incidents") or []
	errors = payload.get("errors") or {}

	_add_site_evidence(site, evidence, causes, next_steps)
	_add_bench_evidence(bench, evidence, causes, next_steps)
	_add_deployment_evidence(deployments, evidence, timeline, causes, next_steps)
	_add_job_evidence(jobs, errors, evidence, timeline, causes, next_steps)
	_add_backup_evidence(backups, evidence, timeline, next_steps)
	_add_domain_evidence(domains, evidence, causes, next_steps)
	_add_incident_evidence(incidents, evidence, timeline, causes, next_steps)

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

	if latest.get("status") in {"Failure", "Fatal", "Cancelled"}:
		evidence.append(f"Latest site update ended with {latest.get('status')}.")
		causes.append("Recent site update failed or was cancelled.")
		next_steps.append(
			"Open the latest Site Update and inspect the linked Agent Job status before retrying."
		)
	elif latest.get("status") in {"Pending", "Running", "Recovering", "Scheduled"}:
		evidence.append(f"Latest site update is {latest.get('status')}.")
		causes.append("A site update is currently pending or running.")
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
		or (deployments and deployments[0].get("status") in {"Failure", "Fatal"})
		or errors.get("failed_job_count")
		or incidents
	)


def _unique(values):
	unique_values = []
	for value in values:
		if value not in unique_values:
			unique_values.append(value)
	return unique_values
