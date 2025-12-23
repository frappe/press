import platform
import sys
from urllib.parse import urljoin

from requests.sessions import Session
from rich.console import Console

console = Console()


# Default User-Agent to identify CLI-originated traffic server-side
CLI_USER_AGENT = (
	f"press-cli/python-{sys.version_info.major}.{sys.version_info.minor}; {platform.system().lower()})"
)


class CloudSession(Session):
	"""Custom requests.Session with Frappe sid cookie"""

	def __init__(self, session_id: str):
		super().__init__()
		self.base_url = "https://frappecloud.com/api/method/"
		self.cookies.set("sid", session_id)

	def request(self, method, url, *args, **kwargs) -> dict[str, str]:
		joined_url = urljoin(self.base_url, url)

		# Inject a default User-Agent header for tracking CLI requests
		headers = kwargs.pop("headers", None) or {}
		headers.setdefault("User-Agent", CLI_USER_AGENT)
		kwargs["headers"] = headers

		if message := kwargs.pop("message", None):
			with console.status(message, spinner="dots"):
				response = super().request(method, joined_url, *args, **kwargs)
		else:
			response = super().request(method, joined_url, *args, **kwargs)

		response.raise_for_status()

		response = response.json()
		if "message" in response:
			return response["message"]
		return response
