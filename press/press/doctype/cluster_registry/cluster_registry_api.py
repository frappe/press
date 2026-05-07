# Handles all API calls to harbor to enabled automated
# - Project creation
# - User creation
# - Retention rules
# - Garbage collection rules


from dataclasses import dataclass
from urllib.parse import urljoin

import requests


@dataclass
class ClusterRegistryAPI:
	harbor_url: str
	harbor_admin_password: str
	harbor_admin_user: str = "admin"
	verify_ssl: bool = False

	def __post_init__(self):
		self.session = requests.Session()
		self.session.verify = self.verify_ssl
		self.session.headers.update(
			{
				"Content-Type": "application/json",
				"accept": "application/json",
			}
		)
		self.session.auth = (self.harbor_admin_user, self.harbor_admin_password)
		self.api_base = urljoin(self.harbor_url, "/api/v2.0/")

	def _request(self, method: str, path: str, **kwargs):
		"""Internal helper to handle URLs and errors"""
		url = urljoin(self.api_base, path.lstrip("/"))
		csrf_header = self.session.get(urljoin(self.api_base, "systeminfo")).headers.get(
			"x-harbor-csrf-token"
		)
		self.session.headers.update({"x-harbor-csrf-token": csrf_header})
		response = self.session.request(method, url, **kwargs)
		response.raise_for_status()
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

	def create_project_robot(self, project_name: str, robot_name: str):
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
		return resp.json()

	def create_project(self, project_name: str, storage_limit: int = -1):
		"""Creates a project if it doesn't exist."""
		payload = {"project_name": project_name, "public": False, "storage_limit": storage_limit}
		# Harbor returns 409 if project exists, we handle that gracefully
		try:
			self._request("POST", "projects", json=payload)
		except requests.exceptions.HTTPError as e:
			if e.response.status_code != 409:
				raise

	def get_project_id(self, project_name: str) -> int:
		"""Helper to fetch the internal integer ID of a project name."""
		resp = self._request("GET", f"projects/{project_name}")
		return resp.json().get("project_id")

	def delete_project_retention(self, project_name: str):
		"""Finds the retention ID for a project and deletes the policy."""
		project_resp = self._request("GET", f"projects/{project_name}")
		project_data = project_resp.json()

		retention_id = project_data.get("metadata", {}).get("retention_id")
		if not retention_id:
			print(f"No retention policy found for project: {project_name}")
			return None

		return self._request("DELETE", f"retentions/{retention_id}")

	def set_retention_rule(self, project_name: str, older_than_days: int = 5):
		"""If the image was pushed more than older_than_days ago, it will be untagged by retention policy."""
		project_id = self.get_project_id(project_name)

		payload = {
			"algorithm": "or",
			"scope": {"level": "project", "ref": project_id},
			"rules": [
				{
					"action": "retain",
					"template": "nDaysSinceLastPush",
					"params": {"nDaysSinceLastPush": str(older_than_days)},
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
				"settings": {"cron": "0 0 1 * * *"},  # Daily at 1 AM
			},
		}
		try:
			existing = self._request("GET", f"projects/{project_name}/summary")
			retention_id = existing.json().get("quota", {}).get("retention_id")
		except Exception:
			retention_id = None

		if retention_id:
			# Update existing policy
			self._request("PUT", f"retentions/{retention_id}", json=payload)
		else:
			# Create new policy
			self._request("POST", "retentions", json=payload)

	def trigger_gc(self):
		"""Manually trigger a Garbage Collection job."""
		payload = {"schedule": {"type": "Manual"}, "parameters": {"delete_untagged": True}}
		return self._request("POST", "system/gc/schedule", json=payload)
