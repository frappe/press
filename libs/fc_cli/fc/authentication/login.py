import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path

import requests

session_file_path = Path(os.path.join(Path(__file__).parent.parent.parent, "session.json"))


@dataclass
class SessionMetadata:
	user_id: str
	sid: str
	full_name: str

	def save(self):
		"""Save session info on base fold"""
		session_path = session_file_path
		with open(session_path, "w") as session_file:
			json.dump(asdict(self), session_file, indent=4)


class OtpLogin:
	def __init__(self, email: str):
		self.email = email
		self.opt_url = "https://frappecloud.com/api/method/press.api.account.send_otp"
		self.login_url = "https://frappecloud.com/api/method/press.api.account.verify_otp_and_login"
		self.me = "https://frappecloud.com/api/method/press.api.account.get"

	def send_otp(self):
		"""Send otp to the email address"""
		response = requests.post(self.opt_url, data={"email": self.email})
		response.raise_for_status()

	def _parse_session_info(self, cookie_data: str, response_data: dict[str, str]) -> SessionMetadata:
		cookies = cookie_data.split(";")
		cookies = [data.strip() for data in cookies]

		for cookie in cookies:
			if "sid" in cookie:
				sid = cookie.replace("sid=", "")
				break

		return SessionMetadata(user_id=self.email, full_name=response_data.get("full_name"), sid=sid)

	def verify_otp_and_get_session_metadata(self, otp) -> SessionMetadata:
		"""Verify otp for user and get session id"""
		login_response = requests.post(self.login_url, data={"email": self.email, "otp": otp})
		login_response.raise_for_status()

		return self._parse_session_info(
			cookie_data=login_response.headers.get("Set-Cookie"), response_data=login_response.json()
		)

	def _check_sid(self, sid: str) -> bool:
		response = requests.get(self.me, cookies={"sid": sid})
		return response.ok

	def verify_existing_session(self) -> bool:
		"""Verify existing session"""
		if not os.path.exists(session_file_path):
			return False

		try:
			with open(session_file_path, "r") as session_file:
				session_data = json.loads(session_file.read())
				sid = session_data.get("sid")
				return self._check_sid(sid)
		except json.decoder.JSONDecodeError:
			return False
