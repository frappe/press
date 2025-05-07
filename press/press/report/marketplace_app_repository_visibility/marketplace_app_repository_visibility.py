import json

import frappe
import requests


def send_developer_email(email, app_name, repository_url):
	dev = frappe.get_doc("User", {"email": email})
	developer_name = dev.full_name
	email_args = {
		"recipients": email,
		"subject": "Frappe Cloud: Make your app's GitHub Repository Public",
		"template": "marketplace_app_visibility",
		"args": {
			"developer_name": developer_name,
			"app_name": app_name,
			"repository_url": repository_url,
		},
	}
	frappe.enqueue(method=frappe.sendmail, queue="short", timeout=300, **email_args)


@frappe.whitelist()
def send_emails(columns, data):
	frappe.only_for("System Manager")
	data = json.loads(data)
	for row in data:
		visibility = row.get("visibility")
		if visibility != "Private":
			continue
		app_name = row.get("app_name")
		repository_url = row.get("repository_url")
		email = row.get("team")
		send_developer_email(email, app_name, repository_url)


def check_repository_visibility(repository_url, personal_access_token):
	try:
		repo_parts = repository_url.split("github.com/")[1].removesuffix(".git").split("/")
		owner = repo_parts[0]
		repo_name = repo_parts[1]
	except IndexError:
		return "Error: Invalid repository URL format."

	api_url = f"https://api.github.com/repos/{owner}/{repo_name}"

	headers = {"Authorization": f"token {personal_access_token}"}

	try:
		response = requests.get(api_url, headers=headers)

		if response.status_code == 200:
			repo_data = response.json()
			if repo_data.get("private"):
				return "Private"
			return "Public"
		if response.status_code == 404:
			return "Private"
		return "Private"
	except Exception:
		return "Error"


def execute(filters=None):
	frappe.only_for("System Manager")

	columns = [
		{"fieldname": "app_name", "label": "Application Name", "fieldtype": "Data", "width": 200},
		{"fieldname": "team", "label": "Team", "fieldtype": "Data", "width": 200},
		{"fieldname": "repository_url", "label": "Repository URL", "fieldtype": "Data", "width": 300},
		{
			"fieldname": "visibility",
			"label": "Visibility",
			"fieldtype": "Data",
			"width": 100,
		},
	]

	data = frappe.db.sql(
		"""
        SELECT
			ma.name AS app_name,
			t.user AS team,
			asrc.repository_url AS repository_url
		FROM
			`tabMarketplace App` ma
		JOIN
			`tabMarketplace App Version` mav ON ma.name = mav.parent
		JOIN
			`tabApp Source` asrc ON mav.source = asrc.name
		JOIN
			`tabTeam` t ON ma.team = t.name
		WHERE
			asrc.enabled = 1 AND
			ma.status = 'Published'
		GROUP BY
			repository_url
        """,
		as_dict=True,
	)
	personal_access_token = frappe.db.get_value("Press Settings", "None", "github_pat_token")

	visibility_cache = {}
	for row in data:
		repo_url = row["repository_url"]
		# Check if the visibility status is already cached for this repository URL
		if repo_url in visibility_cache:
			row["visibility"] = visibility_cache[repo_url]
		else:
			# Check visibility status and cache it
			visibility_status = check_repository_visibility(repo_url, personal_access_token)
			row["visibility"] = visibility_status
			# Store the result in the cache for future reference
			visibility_cache[repo_url] = visibility_status
	return columns, data
