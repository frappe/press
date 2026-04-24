import codeop

import jinja2
from jinja2 import Environment, Template


def eval_example(user_input):
	# ruleid: frappe-codeinjection-eval
	eval(user_input)


def exec_example(user_input):
	# ruleid: frappe-codeinjection-eval
	exec(user_input)


def compile_example(user_input):
	# ruleid: frappe-codeinjection-eval
	compile(user_input, "<string>", "exec")


def codeop_example(user_input):
	# ruleid: frappe-codeinjection-eval
	codeop.compile_command(user_input)


def ssti_example(user_template):
	import frappe

	# ruleid: frappe-ssti
	frappe.render_template(user_template, {})


def jinja_env_example():
	# ruleid: frappe-direct-jinja-construction
	jinja2.Environment(autoescape=False)


def jinja_template_example(user_source):
	# ruleid: frappe-direct-jinja-construction
	Template(user_source)


def jinja_alias_example(user_source):
	# ruleid: frappe-direct-jinja-construction
	Environment(autoescape=False)


def ok_literal_eval(user_input):
	import ast

	# ok: frappe-codeinjection-eval
	return ast.literal_eval(user_input)
