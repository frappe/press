"""Scheduled runner for the Playwright signup E2E test.

Site Config Keys:
    enable_signup_e2e: truthy (1/true/yes/on) to run during scheduled job.
    signup_e2e_base_url: override BASE_URL (defaults to frappe.utils.get_url()).
    signup_e2e_timeout_seconds: overall subprocess timeout (default 900).
    signup_e2e_otp_helper_endpoint: forwarded to OTP_HELPER_ENDPOINT for the test.

"""

from __future__ import annotations

import contextlib
import os
import random
import signal
import subprocess
from pathlib import Path

import frappe

TRUTHY = {"1", "true", "yes", "on"}


def _truthy(val: object) -> bool:
	if val is None:
		return False
	if isinstance(val, bool):
		return val
	return str(val).lower() in TRUTHY


def run_signup_e2e():  # noqa: C901
	if not _truthy(frappe.conf.get("enable_signup_e2e")):
		return

	app_root = Path(__file__).resolve().parent.parent  # .../apps/press
	dashboard_dir = app_root / "dashboard"

	if not dashboard_dir.exists():
		frappe.log(f"signup_e2e: dashboard directory not found at {dashboard_dir}")
		return

	product_trials_list = frappe.db.get_all(
		"Product Trial",
		filters={"published": 1},
		pluck="name",
		order_by="name asc",
	)
	if not product_trials_list:
		frappe.log("signup_e2e: no published product trials found; aborting run")
		return

	random.shuffle(product_trials_list)
	product_trials_list = product_trials_list[:3]

	base_url = frappe.conf.get("signup_e2e_base_url") or frappe.utils.get_url()
	timeout = int(frappe.conf.get("signup_e2e_timeout_seconds") or 900)
	otp_helper = frappe.conf.get("signup_e2e_otp_helper_endpoint")

	env = os.environ.copy()
	env["PRODUCT_TRIALS"] = ",".join(product_trials_list)
	env["BASE_URL"] = base_url
	if otp_helper:
		env["OTP_HELPER_ENDPOINT"] = str(otp_helper)

	cmd = ["npm", "run", "test:e2e", "--", "--project=cron"]
	frappe.log(
		f"signup_e2e: starting Playwright test (products={env.get('PRODUCT_TRIALS')} base_url={env.get('BASE_URL')} timeout={timeout}s)"
	)

	try:
		proc = subprocess.Popen(
			cmd,
			cwd=str(dashboard_dir),
			stdout=subprocess.PIPE,
			stderr=subprocess.STDOUT,
			env=env,
			text=True,
		)
	except FileNotFoundError:
		frappe.log("signup_e2e: failed to spawn npm (is Node/npm installed in this environment?)")
		return

	output_lines = []
	try:
		try:
			while True:
				line = proc.stdout.readline()  # type: ignore[attr-defined]
				if not line and proc.poll() is not None:
					break
				if line:
					output_lines.append(line.rstrip())
		except Exception:
			remaining, _ = proc.communicate(timeout=max(5, timeout // 3))
			if remaining:
				output_lines.append(remaining)
		proc.wait(timeout=timeout)
	except subprocess.TimeoutExpired:
		frappe.log(f"signup_e2e: timeout after {timeout}s; terminating process")
		with contextlib.suppress(Exception):
			proc.send_signal(signal.SIGINT)
		with contextlib.suppress(Exception):
			proc.kill()
	except Exception as e:
		frappe.log(f"signup_e2e: unexpected error: {e}")

	exit_code = proc.returncode if proc.returncode is not None else -1

	MAX_LINES = 2000
	if len(output_lines) > MAX_LINES:
		trimmed = len(output_lines) - MAX_LINES
		output_lines = output_lines[-MAX_LINES:]
		output_lines.insert(0, f"[signup_e2e] (truncated {trimmed} earlier lines)")

	frappe.log(
		f"signup_e2e: completed with exit_code={exit_code} lines={len(output_lines)}\n"
		+ "\n".join(output_lines)
	)

	if exit_code != 0:
		frappe.log_error(
			title="Signup E2E failed",
			message=f"Exit code: {exit_code}\nLast 50 lines:\n" + "\n".join(output_lines[-50:]),
		)

	clean_up()


def clean_up():
	signup_teams = frappe.db.get_all(
		"Team", {"user": ("like", "%fc-signup-test+%"), "enabled": 1}, pluck="name"
	)
	if not signup_teams:
		return

	trial_sites = frappe.db.get_all(
		"Site",
		{"team": ("in", signup_teams), "status": "Active", "standby_for_product": ("is", "set")},
		pluck="name",
	)
	for site in trial_sites:
		try:
			frappe.get_doc("Site", site).archive()
			frappe.db.commit()
		except Exception:
			frappe.db.rollback()

	frappe.db.set_value("Team", {"name": ("in", signup_teams)}, "enabled", 0)
	frappe.db.commit()


__all__ = ["run_signup_e2e"]
