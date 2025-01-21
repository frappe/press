import frappe
import requests


def check_repository_visibility(repository_url, personal_access_token):
	try:
		repo_parts = repository_url.split("github.com/")[1].rstrip(".git").split("/")
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
			return "Error"
		return "Error"
	except Exception:
		return "Error"


def execute(filters=None):
	frappe.only_for("System Manager")

	columns = [
		{"fieldname": "app_name", "label": "Application Name", "fieldtype": "Data", "width": 200},
		{"fieldname": "version", "label": "Version", "fieldtype": "Data", "width": 100},
		{"fieldname": "source", "label": "Source", "fieldtype": "Data", "width": 100},
		{"fieldname": "repository_url", "label": "Repository URL", "fieldtype": "Data", "width": 300},
		{"fieldname": "branch", "label": "Branch", "fieldtype": "Data", "width": 100},
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
            mav.version AS version,
            mav.source AS source,
            asrc.repository_url AS repository_url,
            asrc.branch AS branch
        FROM
            `tabMarketplace App` ma
        JOIN
            `tabMarketplace App Version` mav ON ma.name = mav.parent
        JOIN
            `tabApp Source` asrc ON mav.source = asrc.name
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
