# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt


from functools import partial

import frappe
from ansible.utils.path import cleanup_tmp_file
from frappe.core.doctype.user.user import User
from frappe.handler import is_whitelisted
from frappe.utils import cint

from press.runner import constants
from press.utils import _get_current_team, _system_user


@frappe.whitelist(allow_guest=True)
def upload_file():
	if frappe.session.user == "Guest":
		return None

	files = frappe.request.files
	is_private = frappe.form_dict.is_private
	doctype = frappe.form_dict.doctype
	docname = frappe.form_dict.docname
	fieldname = frappe.form_dict.fieldname
	file_url = frappe.form_dict.file_url
	folder = frappe.form_dict.folder or "Home"
	method = frappe.form_dict.method
	content = None
	filename = None

	if "file" in files:
		file = files["file"]
		content = file.stream.read()
		filename = file.filename

	frappe.local.uploaded_file = content
	frappe.local.uploaded_filename = filename

	if method:
		method = frappe.get_attr(method)
		is_whitelisted(method)
		return method()
	ret = frappe.get_doc(
		{
			"doctype": "File",
			"attached_to_doctype": doctype,
			"attached_to_name": docname,
			"attached_to_field": fieldname,
			"folder": folder,
			"file_name": filename,
			"file_url": file_url,
			"is_private": cint(is_private),
			"content": content,
		}
	)
	ret.save()
	return ret


def on_session_creation():
	from press.utils import get_current_team

	if (
		not frappe.db.exists("Team", {"user": frappe.session.user})
		and frappe.session.data.user_type == "System User"
	):
		return

	try:
		team = get_current_team(get_doc=True)
		route = team.get_route_on_login()
		frappe.local.response.update({"dashboard_route": route})
	except Exception:
		pass


def before_job():
	frappe.local.team = _get_current_team
	frappe.local.system_user = _system_user


def before_request():
	frappe.local.team = _get_current_team
	frappe.local.system_user = _system_user


def cleanup_ansible_tmp_files():
	if hasattr(constants, "DEFAULT_LOCAL_TMP"):
		cleanup_tmp_file(constants.DEFAULT_LOCAL_TMP)


def after_job():
	cleanup_ansible_tmp_files()


def update_website_context(context):
	if (frappe.request and frappe.request.path.startswith("/docs")) and not frappe.db.get_single_value(
		"Press Settings", "publish_docs"
	):
		raise frappe.DoesNotExistError


def has_permission(doc, ptype, user):
	from press.utils import get_current_team, has_role

	if not user:
		user = frappe.session.user

	user_type = frappe.db.get_value("User", user, "user_type", cache=True)
	if user_type == "System User":
		return True

	if ptype == "create":
		return True

	if has_role("Press Support Agent", user) and ptype == "read":
		return True

	team = get_current_team(True)
	child_team_members = [d.name for d in frappe.db.get_all("Team", {"parent_team": team.name}, ["name"])]
	if doc.team == team.name or doc.team in child_team_members:
		return True

	return False


def get_permission_query_conditions_for_doctype_and_user(doctype, user):
	from press.utils import get_current_team

	if not user:
		user = frappe.session.user

	user_type = frappe.db.get_value("User", user, "user_type", cache=True)
	if user_type == "System User":
		return ""

	team = get_current_team()

	return f"(`tab{doctype}`.`team` = {frappe.db.escape(team)})"


def get_permission_query_conditions_for_doctype(doctype):
	return partial(get_permission_query_conditions_for_doctype_and_user, doctype)


class CustomUser(User):
	dashboard_fields = ("full_name", "email", "user_image", "enabled", "user_type")

	@staticmethod
	def get_list_query(query):
		team = frappe.local.team()
		allowed_users = [d.user for d in team.team_members]
		User = frappe.qb.DocType("User")
		return query.where(User.name.isin(allowed_users))

	def after_rename(self, old_name, new_name, merge=False):
		"""
		Changes:
		- Excluding update operations on MyISAM tables
		"""
		myisam_tables = frappe.db.sql_list(
			"""SELECT
			TABLE_NAME FROM information_schema.TABLES
		WHERE
			ENGINE='MyISAM'
		AND TABLE_SCHEMA NOT IN ('mysql','information_schema','performance_schema')
		"""
		)
		tables = [x for x in frappe.db.get_tables() if x not in myisam_tables]

		for tab in tables:
			desc = frappe.db.get_table_columns_description(tab)
			has_fields = []
			for d in desc:
				if d.get("name") in ["owner", "modified_by"]:
					has_fields.append(d.get("name"))
			for field in has_fields:
				frappe.db.sql(
					"""UPDATE `{}`
					SET `{}` = {}
					WHERE `{}` = {}""".format(tab, field, "%s", field, "%s"),
					(new_name, old_name),
				)

		for dt in ["Chat Profile", "Notification Settings"]:
			if frappe.db.exists(dt, old_name):
				frappe.rename_doc(dt, old_name, new_name, force=True, show_alert=False)

		# set email
		frappe.db.sql(
			"""UPDATE `tabUser`
			SET email = %s
			WHERE name = %s""",
			(new_name, new_name),
		)
