from typing import Literal


def api_key(scope: Literal["billing"]) -> str:
	match scope:
		case "billing":
			return "allow_billing"
		case _:
			return ""
