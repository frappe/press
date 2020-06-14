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
		self._read_requirements()
	def _screen_python_files(self):
		files = glob.glob(self.directory + "/**/*.py", recursive=True)
		result = []
		for file in files:
			lines = self._screen_python_file(file)
			if lines:
				name = file.replace(self.directory, "", 1)[1:]
				f = {
					"name": name,
					"id": name.replace("/", "_").replace(".", "_"),
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
				lines_with_issues.append(
					{"lineno": index + 1, "issues": issues, "context": context}
				)
		return lines_with_issues


	def _read_requirements(self):
		requirements_txt = os.path.join(self.directory, "requirements.txt")
		if os.path.exists(requirements_txt):
			with open(requirements_txt) as f:
				self.requirements = f.read()


def get_context(lines, index, size=2):
	length = len(lines)
	lines = lines[max(0, index - size) : min(index + size + 1, length)]  # noqa
	code = "\n".join(lines)
	formatter = HF(
		linenos="table",
		linenostart=max(1, index - size + 1),
		hl_lines=[index - max(0, index - size) + 1],
	)
	lexer = PL(tabsize=4)
	highlighted = highlight(code, lexer, formatter)
	return highlighted


