# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import glob
import json
import os
import regex
import shutil
import subprocess
import frappe
from frappe.model.document import Document
from press.api.github import get_access_token
from press.utils import log_error
from pygments import highlight
from pygments.lexers import PythonLexer as PL
from pygments.formatters import HtmlFormatter as HF


class AppRelease(Document):
	def after_insert(self):
		auto_deploy, skip_review = frappe.db.get_value(
			"Frappe App", self.app, ["enable_auto_deploy", "skip_review"]
		)
		if auto_deploy:
			self.deployable = True
			self.save()
		if skip_review:
			self.status = "Approved"
		else:
			frappe.enqueue_doc(self.doctype, self.name, "screen", enqueue_after_commit=True)

	def on_update(self):
		if self.status == "Approved" and self.deployable:
			self.create_deploy_candidates()

	def create_deploy_candidates(self):
		candidates = frappe.get_all(
			"Deploy Candidate App Release",
			fields=["parent"],
			filters={"app": self.app, "release": self.name},
		)
		if candidates:
			return

		for group_app in frappe.get_all(
			"Release Group Frappe App", fields=["parent"], filters={"app": self.app}
		):
			group = frappe.get_doc("Release Group", group_app.parent)
			group.create_deploy_candidate()

	def deploy(self):
		if self.status == "Approved" and not self.deployable:
			self.deployable = True
			self.save()

	def screen(self):
		try:
			self._set_baseline()

			self._prepare_for_cloning()
			self._clone_repo()

			self._screen_python_files()
			self._filter_results()
			self._render_html()

			self._read_requirements()
			self._filter_requirements()
			self._approve_if_no_issues_found()

			self.save()
		except Exception:
			log_error("App Release Screen Error", release=self.name)

	def run(self, command):
		return subprocess.check_output(
			command.split(), stderr=subprocess.STDOUT, cwd=self.directory
		).decode()

	def _set_baseline(self):
		approved_releases = frappe.get_all(
			"App Release",
			fields=["name", "result", "requirements"],
			filters={"status": "Approved", "app": self.app, "name": ("!=", self.name)},
			order_by="creation desc",
			limit=1,
		)
		if approved_releases:
			baseline = approved_releases[0]
			self.baseline_release = baseline.name
			self.baseline_result = baseline.result
			self.baseline_requirements = baseline.requirements

	def _prepare_for_cloning(self):
		clone_directory = frappe.db.get_single_value("Press Settings", "clone_directory")
		code_server = frappe.db.get_single_value("Press Settings", "code_server")
		if not os.path.exists(clone_directory):
			os.mkdir(clone_directory)

		self.directory = os.path.join(clone_directory, self.hash[:10])
		if os.path.exists(self.directory):
			shutil.rmtree(self.directory)

		os.mkdir(self.directory)

		code_server_url = f"{code_server}/?folder=/home/coder/project/{self.hash[:10]}"
		self.code_server_url = code_server_url

	def _clone_repo(self):
		app = frappe.get_doc("Frappe App", self.app)
		token = get_access_token(app.installation)
		url = f"https://x-access-token:{token}@github.com/{app.repo_owner}/{app.repo}"
		self.output = ""
		self.output += self.run("git init")
		self.output += self.run(f"git remote add origin {url}",)
		self.output += self.run("git config credential.helper ''")
		self.output += self.run(f"git fetch --depth 1 origin {self.hash}")
		self.output += self.run(f"git checkout {self.hash}")

	def _screen_python_files(self):
		files = glob.glob(self.directory + "/**/*.py", recursive=True)
		result = []
		for file in files:
			lines = self._screen_python_file(file)
			if lines:
				name = file.replace(self.directory, "", 1)[1:]
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
					re = regex.compile(pattern)
					search = re.search(line)
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
		if self.baseline_release:
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
			"press/press/doctype/app_release/app_release.html",
			{"result": diff_result, "styles": styles},
		)
		self.result_html = html

	def _read_requirements(self):
		requirements_txt = os.path.join(self.directory, "requirements.txt")
		if os.path.exists(requirements_txt):
			with open(requirements_txt) as f:
				self.requirements = f.read()
		else:
			self.requirements = ""

	def _filter_requirements(self):
		if self.baseline_requirements:
			diff = [
				r for r in self.requirements.splitlines() if r not in self.baseline_requirements
			]
			self.diff_requirements = "\n".join(diff)
		else:
			self.diff_requirements = self.requirements

	def _approve_if_no_issues_found(self):
		if not json.loads(self.diff_result) and not self.diff_requirements:
			self.status = "Approved"
		else:
			self.status = "Awaiting Approval"


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
