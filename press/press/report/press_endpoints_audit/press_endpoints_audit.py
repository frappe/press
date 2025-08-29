# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

import ast
import logging
from collections.abc import Generator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import frappe
import frappe.utils

COLUMNS = [
	{
		"fieldname": "file_path",
		"label": "Path",
		"fieldtype": "Data",
	},
	{
		"fieldname": "line_number",
		"label": "Line",
		"fieldtype": "Int",
	},
	{
		"fieldname": "function_name",
		"label": "Function",
		"fieldtype": "Data",
	},
	{
		"fieldname": "is_whitelisted",
		"label": "Whitelisted",
		"fieldtype": "Check",
	},
	{
		"fieldname": "is_protected",
		"label": "Protected",
		"fieldtype": "Check",
	},
	{
		"fieldname": "protected_doctypes",
		"label": "Protected Doctypes",
		"fieldtype": "Data",
	},
	{
		"fieldname": "is_get_doc_with_input",
		"label": "Uses get_doc with input",
		"fieldtype": "Check",
	},
	{
		"fieldname": "parameters",
		"label": "Parameters",
		"fieldtype": "Data",
	},
]


@dataclass
class FunctionAnalysis:
	file_path: str
	function_name: str
	line_number: int
	is_whitelisted: bool = False
	is_protected: bool = False
	protected_doctypes: list[str] = field(default_factory=list)
	has_get_doc_with_input: bool = False
	parameters: list[str] = field(default_factory=list)

	def to_dict(self) -> dict[str, Any]:
		return {
			"file_path": self.file_path,
			"function_name": self.function_name,
			"line_number": self.line_number,
			"is_whitelisted": 1 if self.is_whitelisted else 0,
			"is_protected": 1 if self.is_protected else 0,
			"protected_doctypes": ", ".join(self.protected_doctypes),
			"is_get_doc_with_input": 1 if self.has_get_doc_with_input else 0,
			"parameters": ", ".join(self.parameters),
		}


class ASTAnalyzer:
	@staticmethod
	def parse_file(file_path: str | Path) -> ast.AST | None:
		try:
			with open(file_path, "r", encoding="utf-8") as f:
				content = f.read()
			return ast.parse(content, filename=str(file_path))
		except (OSError, SyntaxError, UnicodeDecodeError) as e:
			logging.warning(f"Failed to parse file {file_path}: {e}")
			return None

	@staticmethod
	def is_function_call_decorator(decorator: ast.AST) -> bool:
		return isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute)

	@staticmethod
	def is_whitelisted_function(node: ast.FunctionDef) -> bool:
		for decorator in node.decorator_list:
			if not ASTAnalyzer.is_function_call_decorator(decorator):
				continue

			func = decorator.func
			if (
				hasattr(func, "value")
				and isinstance(func.value, ast.Name)
				and func.value.id == "frappe"
				and func.attr == "whitelist"
			):
				return True
		return False

	@staticmethod
	def get_protected_doctypes(node: ast.FunctionDef) -> list[str] | None:
		for decorator in node.decorator_list:
			if isinstance(decorator, ast.Call):
				func = decorator.func
				if isinstance(func, ast.Name) and func.id == "protected":
					if not decorator.args:
						return []

					arg = decorator.args[0]
					if isinstance(arg, ast.Constant):
						return [str(arg.value)]
					if isinstance(arg, ast.List):
						return [str(elt.value) for elt in arg.elts if isinstance(elt, ast.Constant)]
			elif isinstance(decorator, ast.Name) and decorator.id == "protected":
				return []

		return None

	@staticmethod
	def get_function_parameters(node: ast.FunctionDef) -> list[str]:
		return [arg.arg for arg in node.args.args]

	@staticmethod
	def uses_get_doc_with_input(node: ast.AST, params: list[str]) -> bool:
		if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Call):
			return False

		call_node = node.value
		if not (
			isinstance(call_node.func, ast.Attribute)
			and isinstance(call_node.func.value, ast.Name)
			and call_node.func.value.id == "frappe"
			and call_node.func.attr == "get_doc"
		):
			return False
		return any(isinstance(arg, ast.Name) and arg.id in params for arg in call_node.args)


class EndpointAuditor:
	def __init__(self, root_directory: str | Path):
		self.root_directory = Path(root_directory).resolve()
		self.analyzer = ASTAnalyzer()

	def analyze_function(self, node: ast.FunctionDef, file_path: Path) -> FunctionAnalysis:
		parameters = self.analyzer.get_function_parameters(node)
		protected_doctypes = self.analyzer.get_protected_doctypes(node)

		has_get_doc_with_input = any(
			self.analyzer.uses_get_doc_with_input(n, parameters) for n in ast.walk(node)
		)

		relative_path = str(file_path.relative_to(self.root_directory))

		return FunctionAnalysis(
			file_path=relative_path,
			function_name=node.name,
			line_number=node.lineno,
			is_whitelisted=self.analyzer.is_whitelisted_function(node),
			is_protected=protected_doctypes is not None,
			protected_doctypes=protected_doctypes or [],
			has_get_doc_with_input=has_get_doc_with_input,
			parameters=parameters,
		)

	def analyze_file(self, file_path: Path) -> Generator[FunctionAnalysis, None, None]:
		tree = self.analyzer.parse_file(file_path)
		if tree is None:
			return

		for node in ast.walk(tree):
			if isinstance(node, ast.FunctionDef):
				yield self.analyze_function(node, file_path)

	def audit_directory(self) -> Generator[FunctionAnalysis, None, None]:
		try:
			for file_path in self.root_directory.rglob("*.py"):
				if file_path.is_file():
					yield from self.analyze_file(file_path)
		except OSError as e:
			logging.error(f"Error walking directory {self.root_directory}: {e}")
			frappe.throw(f"Failed to access directory: {e}")


def execute() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
	bench_root = Path(frappe.utils.get_bench_path()).resolve()
	audit_directory = bench_root.joinpath("apps", "press", "press")
	auditor = EndpointAuditor(audit_directory)
	analyses = list(auditor.audit_directory())
	data = [analysis.to_dict() for analysis in analyses]
	return COLUMNS, data
