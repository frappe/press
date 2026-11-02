from typing import Literal


def api_key(scope: Literal["billing", "partner"]) -> str:
	match scope:
		case "billing":
			return "allow_billing"
		case "partner":
			return "allow_partner"
		case _:
			return ""
