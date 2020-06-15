# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import glob
import json
import os
import regex
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
		auto_approve = frappe.db.get_value("Frappe App", self.app, "auto_approve")
		if auto_approve:
			self.status = "Approved"
			self.save()
		self.create_deploy_candidates()

	def create_deploy_candidates(self):
		for group_app in frappe.get_all(
			"Release Group Frappe App", fields=["parent"], filters={"app": self.app}
		):
			group = frappe.get_doc("Release Group", group_app.parent)
			group.create_deploy_candidate()

	def deploy(self):
		if self.status == "Approved":
			pass

	def request_approval(self):
		if self.status == "":
			self.status = "Awaiting Approval"
			self.save()
			frappe.enqueue_doc(
				self.doctype, self.name, "clone_locally", enqueue_after_commit=True
			)

	def approve(self):
		if self.status == "Awaiting Approval":
			self.status = "Approved"
			self.save()

	def reject(self, reason):
		if self.status == "Awaiting Approval":
			self.status = "Rejected"
			self.save()

	def clone_locally(self):
		try:
			directory = frappe.db.get_single_value("Press Settings", "clone_directory")
			code_server = frappe.db.get_single_value("Press Settings", "code_server")
			if not os.path.exists(directory):
				os.mkdir(directory)

			self.directory = os.path.join(directory, self.hash[:10])
			code_server_url = f"{code_server}/?folder=/home/coder/project/{self.hash[:10]}"
			self.code_server_url = code_server_url
			self.save()
			if not os.path.exists(self.directory):
				os.mkdir(self.directory)

			app = frappe.get_doc("Frappe App", self.app)
			token = get_access_token(app.installation)

			subprocess.run("git init".split(), check=True, cwd=self.directory)
			subprocess.run(
				f"git remote add origin https://x-access-token:{token}@github.com/{app.repo_owner}/{app.repo}".split(),
				check=True,
				cwd=self.directory,
			)
			subprocess.run(
				f"git fetch --depth 1 origin {self.hash}".split(), check=True, cwd=self.directory
			)
			subprocess.run(f"git checkout {self.hash}".split(), check=True, cwd=self.directory)

			frappe.enqueue_doc(self.doctype, self.name, "screen", enqueue_after_commit=True)
		except Exception:
			log_error("Clone Error", release=self.name)

	def screen(self):
		result = self._screen_python_files()
		self._render_html(result)
		self._read_requirements()
		self.save()

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
		self.result = json.dumps(result, indent=4)
		return result

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

	def _render_html(self, result):
		formatter = HF()
		styles = f"<style>{formatter.get_style_defs()}</style>"
		for file in result:
			file["id"] = file["name"].replace("/", "_").replace(".", "_")
			for line in file["lines"]:
				line["highlighted_context"] = highlight_context(line["context"])
		html = frappe.render_template(
			"press/press/doctype/app_release/app_release.html",
			{"result": result, "styles": styles},
		)
		self.result_html = html

	def _read_requirements(self):
		requirements_txt = os.path.join(self.directory, "requirements.txt")
		if os.path.exists(requirements_txt):
			with open(requirements_txt) as f:
				self.requirements = f.read()


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
		linenos="table", linenostart=line_range[0], hl_lines=[line_number - line_range[0]],
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
