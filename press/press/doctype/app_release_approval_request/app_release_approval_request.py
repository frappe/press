# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

import json
import re
import glob
from pygments.lexers import PythonLexer as PL
from pygments.formatters import HtmlFormatter as HF
from pygments import highlight

import frappe
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from press.press.doctype.app_release.app_release import AppRelease


class AppReleaseApprovalRequest(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		app: DF.Link | None
		app_release: DF.Link
		baseline_request: DF.Data | None
		baseline_requirements: DF.Code | None
		baseline_result: DF.Code | None
		marketplace_app: DF.Link
		reason_for_rejection: DF.TextEditor | None
		requirements: DF.Code | None
		result: DF.Code | None
		result_html: DF.Code | None
		reviewed_by: DF.Link | None
		screening_status: DF.Literal["Not Started", "Screening", "Complete"]
		status: DF.Literal["Open", "Cancelled", "Approved", "Rejected"]
		team: DF.Link | None
	# end: auto-generated types

	def before_save(self):
		apps = frappe.get_all("Featured App", {"parent": "Marketplace Settings"}, pluck="app")
		teams = frappe.get_all(
			"Auto Release Team", {"parent": "Marketplace Settings"}, pluck="team"
		)
		if self.team in teams or self.marketplace_app in apps:
			self.status = "Approved"

	@staticmethod
	def create(marketplace_app: str, app_release: str):
		"""Create a new `App Release Approval Request`"""
		request = frappe.new_doc("App Release Approval Request")
		request.marketplace_app = marketplace_app
		request.app_release = app_release
		request.save(ignore_permissions=True)

	def cancel(self):
		self.status = "Cancelled"
		self.save(ignore_permissions=True)

	def autoname(self):
		app = self.marketplace_app
		series = f"REQ-{app}-.#####"
		self.name = make_autoname(series)

	def before_insert(self):
		self.request_already_exists()
		self.another_request_awaiting_approval()
		self.update_release_status()

	def request_already_exists(self):
		requests = frappe.get_all(
			"App Release Approval Request",
			filters={"app_release": self.app_release, "status": ("!=", "Cancelled")},
		)

		if len(requests) > 0:
			frappe.throw("An active request for this app release already exists!")

	def another_request_awaiting_approval(self):
		request_source = frappe.db.get_value("App Release", self.app_release, "source")

		releases_awaiting_approval = frappe.get_all(
			"App Release Approval Request",
			filters={"marketplace_app": self.marketplace_app, "status": "Open"},
			pluck="app_release",
		)
		sources_awaiting_approval = [
			frappe.db.get_value("App Release", r, "source") for r in releases_awaiting_approval
		]

		# A request for this source is already open
		if request_source in sources_awaiting_approval:
			frappe.throw("A previous release is already awaiting approval!")

	def update_release_status(self):
		release: AppRelease = frappe.get_doc("App Release", self.app_release)
		release.status = "Awaiting Approval"
		release.save(ignore_permissions=True)

	def on_update(self):
		old_doc = self.get_doc_before_save()

		if old_doc is None:
			return

		status_updated = old_doc.status != self.status
		release = frappe.get_doc("App Release", self.app_release)

		if status_updated and self.status == "Rejected":
			release.status = "Rejected"
			self.notify_publisher()
		elif status_updated and self.status == "Approved":
			release.status = "Approved"
			self.notify_publisher()
		elif status_updated and self.status == "Cancelled":
			release.status = "Draft"

		release.save(ignore_permissions=True)
		frappe.db.commit()

		if status_updated:
			self.publish_status_change(release.source)

	def publish_status_change(self, source):
		frappe.publish_realtime(event="request_status_changed", message={"source": source})

	def notify_publisher(self):
		marketplace_app = frappe.get_doc("Marketplace App", self.marketplace_app)
		app_release: AppRelease = frappe.get_doc("App Release", self.app_release)
		publisher_email = frappe.get_doc("Team", marketplace_app.team).user

		frappe.sendmail(
			[publisher_email],
			subject=f"Frappe Cloud Marketplace: {marketplace_app.title}",
			args={
				"subject": "Update on your app release publish request",
				"status": self.status,
				"rejection_reason": self.reason_for_rejection,
				"commit_message": app_release.message,
				"releases_link": f"{frappe.local.site}/dashboard/marketplace/apps/{self.marketplace_app}/releases",
			},
			template="app_approval_request_update",
		)

	@frappe.whitelist()
	def start_screening(self):
		self.release = frappe.get_doc("App Release", self.app_release, for_update=True)
		self._set_baseline()

		# Clone the release, if not already
		self.release._clone()

		self._screen_python_files()
		self._filter_results()
		self._render_html()

		self.screening_status = "Complete"
		self.save()

	def _set_baseline(self):
		approved_releases = frappe.get_all(
			"App Release Approval Request",
			fields=["name", "result", "requirements"],
			filters={"status": "Approved", "app": self.app, "name": ("!=", self.name)},
			order_by="creation desc",
			limit=1,
		)

		if approved_releases:
			baseline = approved_releases[0]
			self.baseline_request = baseline.name
			self.baseline_result = baseline.result
			self.baseline_requirements = baseline.requirements

	def _screen_python_files(self):
		files = glob.glob(self.release.clone_directory + "/**/*.py", recursive=True)
		result = []
		for file in files:
			lines = self._screen_python_file(file)
			if lines:
				name = file.replace(self.release.clone_directory, "", 1)[1:]
				f = {
					"name": name,
					"lines": lines,
					"score": len(lines),
				}
				result.append(f)
		result = sorted(result, key=lambda x: x["score"], reverse=True)
		self.result = json.dumps(result, indent=2)

	def _screen_python_file(self, filename):
		with open(filename, "r") as ff:
			lines = ff.read().splitlines()
		lines_with_issues = []
		for index, line in enumerate(lines):
			issues = []
			configuration = get_configuration()
			for severity, violations in configuration.items():
				for violation, keywords in violations.items():
					pattern = r"(?:^|\W)({})(?:\W|$)".format("|".join(keywords))
					regex = re.compile(pattern)
					search = regex.search(line)
					if search:
						issues.append(
							{"severity": severity, "violation": violation, "match": search.group(1)}
						)
			if issues:
				context = get_context(lines, index)
				lines_with_issues.append({"issues": issues, "context": context})
		return lines_with_issues

	def _filter_results(self):
		result = json.loads(self.result)
		if self.baseline_request and self.baseline_result:
			baseline_result = json.loads(self.baseline_result)
			diff_result = []
			for file in result:
				if file not in baseline_result:
					diff_result.append(file)
		else:
			diff_result = result
		self.diff_result = json.dumps(diff_result, indent=2)

	def _render_html(self):
		diff_result = json.loads(self.diff_result)
		formatter = HF()
		styles = f"<style>{formatter.get_style_defs()}</style>"
		for file in diff_result:
			file["id"] = file["name"].replace("/", "_").replace(".", "_")
			for line in file["lines"]:
				line["highlighted_context"] = highlight_context(line["context"])
		html = frappe.render_template(
			"press/press/doctype/app_release_approval_request/app_release_approval_request.html",
			{"result": diff_result, "styles": styles},
		)
		self.result_html = html
		self.result_html_rendered = html


def get_context(lines, index, size=2):
	length = len(lines)
	start = max(0, index - size)
	end = min(index + size, length)
	lines = lines[start : end + 1]  # noqa
	return {
		"line_number": index + 1,
		"line_range": list(range(start + 1, end + 2)),
		"lines": lines,
	}


def highlight_context(context):
	line_number = context["line_number"]
	line_range = context["line_range"]
	lines = context["lines"]
	code = "\n".join(lines)
	formatter = HF(
		linenos="table",
		linenostart=line_range[0],
		hl_lines=[line_number - line_range[0] + 1],
	)
	lexer = PL(stripnl=False, tabsize=4)
	highlighted = highlight(code, lexer, formatter)
	return highlighted


def get_configuration():
	return {
		"Critical": {
			"Arbitrary Command Injection": ["os", "sys", "subprocess", "sysconfig"],
			"Arbitrary Command Injection - Frappe": ["popen", "execute_in_shell"],
			"Arbitrary Code Execution": [
				"exec",
				"eval",
				"safe_eval",
				"safe_exec",
				"compile",
				"codeop",
			],
			"Runtime Imports": [
				"__import__",
				"importlib",
				"zipimport",
				"runpy",
				"pkgutil",
				"modulefinder",
			],
			"Runtime Imports - Frappe": ["get_attr", "get_module"],
			"Unsafe Serialization": ["pickle", "marshal"],
			"Template Rendering": ["jinja", "jinja2"],
			"Foreign Functions Library": ["ctypes"],
			"Arbitrary Code Injection - Posix": [
				"signal",
				"syslog",
				"pipes",
				"fcntl",
				"pty",
				"tty",
				"posix",
				"pwd",
				"grp",
				"spwd",
			],
		},
		"Major": {
			"File Manipulation": [
				"open",
				"io",
				"shutil",
				"pathlib",
				"fileinput",
				"sqlite3",
				"gzip",
				"bz2",
				"lzma",
				"zipfile",
			],
			"File Manipulation - Frappe": ["touch_file", "get_file_json", "read_file"],
			"Site Access": ["get_site_config", "get_sites"],
		},
		"Moderate": {
			"Potential Screening Bypass": [
				"globals",
				"builtins",
				"__globals__",
				"__builtins__",
				"__module__",
				"__file__",
				"__func__",
				"__class__",
				"__dict__",
				"__self__",
			],
		},
		"Low": {
			"Debugging": ["inspect", "breakpoint"],
			"Multiprocessing": ["multiprocessing", "threading"],
		},
	}
