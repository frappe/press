# Handles all API calls to harbor to enabled automated
# - Project creation
# - User creation
# - Retention rules
# - Garbage collection rules


import base64
from dataclasses import dataclass
from urllib.parse import urljoin

import requests


@dataclass
class ClusterRegistryAPI:
	harbor_url: str
	harbor_admin_password: str
	harbor_admin_user: str = "admin"

	def __post_init__(self):
		self.api_base = urljoin(self.harbor_url, "/api/v2.0/")

	def _get_headers(self) -> dict[str, str]:
		credentials = base64.b64encode(
			f"{self.harbor_admin_user}:{self.harbor_admin_password}".encode()
		).decode()
		return {
			"Authorization": f"Basic {credentials}",
			"Content-Type": "application/json",
			"accept": "application/json",
		}

	def _request(self, method: str, path: str, **kwargs):
		"""Internal helper to handle URLs and errors"""
		url = urljoin(self.api_base, path.lstrip("/"))
		# Ensure that we won't have cookies (Harbor thinks are we coming from the browser)
		response = requests.request(method, url, **kwargs, headers=self._get_headers())

		try:
			response.raise_for_status()
		except requests.exceptions.HTTPError as e:
			if e.response.status_code != 409:
				raise

		return response

	def statistics(self):
		"""Fetches Harbor statistics, useful for monitoring."""
		return self._request("GET", "statistics").json()

	def health(self) -> bool:
		"""Checks if Harbor is healthy."""
		try:
			resp = self._request("GET", "health")
			return resp.json().get("status") == "healthy"
		except requests.exceptions.RequestException:
			return False

	def get_project_id(self, project_name: str) -> int:
		"""Helper to fetch the internal integer ID of a project name."""
		resp = self._request("GET", f"projects/{project_name}")
		return resp.json().get("project_id")

	def get_retention_id(self, project_name: str) -> int | None:
		"""Helper to fetch the retention ID for a project."""
		project_resp = self._request("GET", f"projects/{project_name}")
		project_data = project_resp.json()
		return project_data.get("metadata", {}).get("retention_id")

	def create_project_robot(self, project_name: str, robot_name: str) -> tuple[str, str]:
		"""Creates a Robot Account for a specific project."""
		payload = {
			"name": robot_name,
			"level": "project",
			"duration": -1,  # Never expires
			"permissions": [
				{
					"kind": "project",
					"namespace": project_name,
					"access": [
						# only give push/pull permissions, no delete or admin rights
						{"resource": "repository", "action": "push"},
						{"resource": "repository", "action": "pull"},
					],
				}
			],
		}
		resp = self._request("POST", "robots", json=payload)
		json_response = resp.json()
		return json_response.get("name"), json_response.get("secret")

	def create_project(self, project_name: str, storage_limit: int = -1):
		"""Creates a project if it doesn't exist."""
		payload = {"project_name": project_name, "public": False, "storage_limit": storage_limit}
		self._request("POST", "projects", json=payload)

	def create_garbage_collection_rule(self, schedule_cron: str):
		"""Creates a GC rule that runs on the specified cron schedule cleaning up untagged images"""
		payload = {
			"schedule": {"type": "Custom", "cron": schedule_cron},
			"parameters": {"delete_untagged": True},
		}
		self._request("POST", "system/gc/schedule", json=payload)

	def create_retention_rule(
		self,
		project_name: str,
		older_than_days: int = 5,
		pushed_based_retention: bool = True,
		cron: str = "0 0 1 * * *",
	):
		"""If the image was pushed more than older_than_days ago, it will be untagged by retention policy."""
		project_id = self.get_project_id(project_name)
		template = "nDaysSinceLastPush" if pushed_based_retention else "nDaysSinceLastPull"

		payload = {
			"algorithm": "or",
			"scope": {"level": "project", "ref": project_id},
			"rules": [
				{
					"action": "retain",
					"template": template,
					"params": {template: str(older_than_days)},
					"tag_selectors": [
						{"kind": "doublestar", "decoration": "matches", "pattern": "**", "untagged": True}
					],
					"scope_selectors": {
						"repository": [{"kind": "doublestar", "decoration": "repoMatches", "pattern": "**"}]
					},
				}
			],
			"trigger": {
				"kind": "Schedule",
				"settings": {"cron": cron},
			},
		}
		retention_id = self.get_retention_id(project_name)

		if retention_id:
			# Update existing policy
			self._request("PUT", f"retentions/{retention_id}", json=payload)
		else:
			# Create new policy
			self._request("POST", "retentions", json=payload)

	def create_project_quota(self, project_name: str, storage_limit: int):
		"""Set storage quota limit for a project based on the disk size of the cluster registry.
		WARNING: Storage limit should be in GB
		"""
		quota_id = None
		project_id = self.get_project_id(project_name)
		quotas = self._request("GET", "quotas").json()
		for quota in quotas:
			if quota.get("ref", {}).get("id") == project_id:
				quota_id = quota.get("id")

		payload = {"hard": {"storage": storage_limit * (1024**3)}}
		self._request("PUT", f"quotas/{quota_id}", json=payload)

	def trigger_retention_execution(self, project_name: str):
		"""Manually trigger a retention policy execution for a project."""
		retention_id = self.get_retention_id(project_name)
		self._request("POST", f"retentions/{retention_id}/executions", json={"dry_run": False})

	def trigger_gc(self):
		"""Manually trigger a Garbage Collection job."""
		payload = {"schedule": {"type": "Manual"}, "parameters": {"delete_untagged": True}}
		return self._request("POST", "system/gc/schedule", json=payload)
