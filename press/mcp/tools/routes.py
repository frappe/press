# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt
from urllib.parse import unquote, urlparse

from press.mcp import mcp as press_mcp
from press.mcp.tools.documents import DOCTYPE_SLUGS
from press.mcp.utils import system_manager_only

DASHBOARD_PREFIX = "/dashboard"
DESK_PREFIXES = {"app", "desk"}

ROUTES = {
	("/sites", ":name", "/insights", "/jobs", ":id"): {
		"route": "/sites/:name/insights/jobs/:id",
		"page": "Agent Job detail inside a Site",
		"primary_param": "id",
		"params": {
			"name": {"represents": "Site", "role": "parent"},
			"id": {"represents": "Agent Job", "role": "primary"},
		},
	},
	("/sites", ":name", "/insights", "/logs", "/view", ":logName"): {
		"route": "/sites/:name/insights/logs/view/:logName",
		"page": "Site log detail",
		"primary_param": "logName",
		"params": {
			"name": {"represents": "Site", "role": "parent"},
			"logName": {"represents": "Log name", "role": "primary"},
		},
	},
	("/sites", ":name", "/updates", ":id"): {
		"route": "/sites/:name/updates/:id",
		"page": "Site Update detail inside a Site",
		"primary_param": "id",
		"params": {
			"name": {"represents": "Site", "role": "parent"},
			"id": {"represents": "Site Update", "role": "primary"},
		},
	},
	("/sites", ":name", "/migrations", ":id"): {
		"route": "/sites/:name/migrations/:id",
		"page": "Site Migration detail inside a Site",
		"primary_param": "id",
		"params": {
			"name": {"represents": "Site", "role": "parent"},
			"id": {"represents": "Site Migration", "role": "primary"},
		},
	},
	("/groups", ":name", "/deploys", ":id"): {
		"route": "/groups/:name/deploys/:id",
		"page": "Deploy Candidate Build detail inside a Release Group",
		"primary_param": "id",
		"params": {
			"name": {
				"represents": "Release Group",
				"role": "parent",
			},
			"id": {
				"represents": "Deploy Candidate Build",
				"role": "primary",
			},
		},
	},
	("/groups", ":name", "/pipelines", ":id"): {
		"route": "/groups/:name/pipelines/:id",
		"page": "Release Pipeline detail inside a Release Group",
		"primary_param": "id",
		"params": {
			"name": {
				"represents": "Release Group",
				"role": "parent",
			},
			"id": {
				"represents": "Release Pipeline",
				"role": "primary",
			},
		},
	},
	("/groups", ":name", "/jobs", ":id"): {
		"route": "/groups/:name/jobs/:id",
		"page": "Agent Job detail inside a Release Group",
		"primary_param": "id",
		"params": {
			"name": {"represents": "Release Group", "role": "parent"},
			"id": {"represents": "Agent Job", "role": "primary"},
		},
	},
	("/benches", ":name", "/jobs", ":id"): {
		"route": "/benches/:name/jobs/:id",
		"page": "Agent Job detail inside a Bench",
		"primary_param": "id",
		"params": {
			"name": {"represents": "Bench", "role": "parent"},
			"id": {"represents": "Agent Job", "role": "primary"},
		},
	},
	("/benches", ":name", "/logs", ":logName"): {
		"route": "/benches/:name/logs/:logName",
		"page": "Bench log detail",
		"primary_param": "logName",
		"params": {
			"name": {"represents": "Bench", "role": "parent"},
			"logName": {"represents": "Log name", "role": "primary"},
		},
	},
	("/servers", ":name", "/jobs", ":id"): {
		"route": "/servers/:name/jobs/:id",
		"page": "Agent Job detail inside a Server",
		"primary_param": "id",
		"params": {
			"name": {"represents": "Server", "role": "parent"},
			"id": {"represents": "Agent Job", "role": "primary"},
		},
	},
	("/servers", ":name", "/plays", ":id"): {
		"route": "/servers/:name/plays/:id",
		"page": "Ansible Play detail inside a Server",
		"primary_param": "id",
		"params": {
			"name": {"represents": "Server", "role": "parent"},
			"id": {"represents": "Ansible Play", "role": "primary"},
		},
	},
	("/servers", ":name", "/auto-scale-steps", ":id"): {
		"route": "/servers/:name/auto-scale-steps/:id",
		"page": "Auto Scale Record detail inside a Server",
		"primary_param": "id",
		"params": {
			"name": {"represents": "Server", "role": "parent"},
			"id": {"represents": "Auto Scale Record", "role": "primary"},
		},
	},
	("/groups", ":name"): {
		"route": "/groups/:name",
		"page": "Release Group detail",
		"primary_param": "name",
		"params": {
			"name": {
				"represents": "Release Group",
				"role": "primary",
			},
		},
	},
	("/groups", ":name", ":tab"): {
		"route": "/groups/:name/:tab",
		"page": "Release Group tab",
		"primary_param": "name",
		"params": {
			"name": {"represents": "Release Group", "role": "primary"},
			"tab": {"represents": "Dashboard tab", "role": "view"},
		},
	},
	("/sites", ":name"): {
		"route": "/sites/:name",
		"page": "Site detail",
		"primary_param": "name",
		"params": {
			"name": {
				"represents": "Site",
				"role": "primary",
			},
		},
	},
	("/sites", ":name", ":tab"): {
		"route": "/sites/:name/:tab",
		"page": "Site tab",
		"primary_param": "name",
		"params": {
			"name": {"represents": "Site", "role": "primary"},
			"tab": {"represents": "Dashboard tab", "role": "view"},
		},
	},
	("/sites", ":name", "/insights", ":view"): {
		"route": "/sites/:name/insights/:view",
		"page": "Site insights view",
		"primary_param": "name",
		"params": {
			"name": {"represents": "Site", "role": "primary"},
			"view": {"represents": "Insights view", "role": "view"},
		},
	},
	("/sites", ":name", "/insights", "/logs", ":type?"): {
		"route": "/sites/:name/insights/logs/:type?",
		"page": "Site logs view",
		"primary_param": "name",
		"params": {
			"name": {"represents": "Site", "role": "primary"},
			"type": {"represents": "Log type", "role": "filter"},
		},
	},
	("/sites", ":name", "/insights", "/performance", ":view"): {
		"route": "/sites/:name/insights/performance/:view",
		"page": "Site performance view",
		"primary_param": "name",
		"params": {
			"name": {"represents": "Site", "role": "primary"},
			"view": {"represents": "Performance view", "role": "view"},
		},
	},
	("/benches", ":name"): {
		"route": "/benches/:name",
		"page": "Bench detail",
		"primary_param": "name",
		"params": {
			"name": {
				"represents": "Bench",
				"role": "primary",
			},
		},
	},
	("/benches", ":name", ":tab"): {
		"route": "/benches/:name/:tab",
		"page": "Bench tab",
		"primary_param": "name",
		"params": {
			"name": {"represents": "Bench", "role": "primary"},
			"tab": {"represents": "Dashboard tab", "role": "view"},
		},
	},
	("/servers", ":name"): {
		"route": "/servers/:name",
		"page": "Server detail",
		"primary_param": "name",
		"params": {
			"name": {
				"represents": "Server",
				"role": "primary",
			},
		},
	},
	("/servers", ":name", ":tab"): {
		"route": "/servers/:name/:tab",
		"page": "Server tab",
		"primary_param": "name",
		"params": {
			"name": {"represents": "Server", "role": "primary"},
			"tab": {"represents": "Dashboard tab", "role": "view"},
		},
	},
	("/servers", ":name", "/auto-scale", ":view"): {
		"route": "/servers/:name/auto-scale/:view",
		"page": "Server auto-scale view",
		"primary_param": "name",
		"params": {
			"name": {"represents": "Server", "role": "primary"},
			"view": {"represents": "Auto-scale view", "role": "view"},
		},
	},
	("/apps", ":name"): {
		"route": "/apps/:name",
		"page": "Marketplace App detail",
		"primary_param": "name",
		"params": {
			"name": {"represents": "Marketplace App", "role": "primary"},
		},
	},
	("/apps", ":name", ":tab"): {
		"route": "/apps/:name/:tab",
		"page": "Marketplace App tab",
		"primary_param": "name",
		"params": {
			"name": {"represents": "Marketplace App", "role": "primary"},
			"tab": {"represents": "Dashboard tab", "role": "view"},
		},
	},
	("/groups", ":bench", "/sites", "/new"): {
		"route": "/groups/:bench/sites/new",
		"page": "New Site inside a Release Group",
		"primary_param": "bench",
		"params": {
			"bench": {"represents": "Release Group", "role": "primary"},
		},
	},
	("/servers", ":server", "/sites", "/new"): {
		"route": "/servers/:server/sites/new",
		"page": "New Site inside a Server",
		"primary_param": "server",
		"params": {
			"server": {"represents": "Server", "role": "primary"},
		},
	},
	("/servers", ":server", "/groups", "/new"): {
		"route": "/servers/:server/groups/new",
		"page": "New Release Group inside a Server",
		"primary_param": "server",
		"params": {
			"server": {"represents": "Server", "role": "primary"},
		},
	},
	("/sites", "/new", "/progress", ":siteGroupDeployName"): {
		"route": "/sites/new/progress/:siteGroupDeployName",
		"page": "New Site progress",
		"primary_param": "siteGroupDeployName",
		"params": {
			"siteGroupDeployName": {"represents": "Site Group Deploy", "role": "primary"},
		},
	},
	("/partner-lead", ":leadId"): {
		"route": "/partner-lead/:leadId",
		"page": "Partner Lead detail",
		"primary_param": "leadId",
		"params": {
			"leadId": {"represents": "Partner Lead", "role": "primary"},
		},
	},
	("/partner-lead", ":leadId", ":tab"): {
		"route": "/partner-lead/:leadId/:tab",
		"page": "Partner Lead tab",
		"primary_param": "leadId",
		"params": {
			"leadId": {"represents": "Partner Lead", "role": "primary"},
			"tab": {"represents": "Dashboard tab", "role": "view"},
		},
	},
	("/partners", "/audit", ":partner_audit?"): {
		"route": "/partners/audit/:partner_audit?",
		"page": "Partner audit non-conformance list",
		"primary_param": "partner_audit",
		"params": {
			"partner_audit": {"represents": "Partner Audit", "role": "primary"},
		},
	},
	("/partners", "/audit", ":partner_audit", "/nc-summary", ":nc?"): {
		"route": "/partners/audit/:partner_audit/nc-summary/:nc?",
		"page": "Partner Non Conformance summary",
		"primary_param": "nc",
		"params": {
			"partner_audit": {"represents": "Partner Audit", "role": "parent"},
			"nc": {"represents": "Partner Non Conformance", "role": "primary"},
		},
	},
	("/settings", "/permissions", "/roles", ":id"): {
		"route": "/settings/permissions/roles/:id",
		"page": "Permission Role detail",
		"primary_param": "id",
		"params": {
			"id": {"represents": "Role", "role": "primary"},
		},
	},
	("/create-site", ":productId", "/setup"): {
		"route": "/create-site/:productId/setup",
		"page": "Signup site setup",
		"primary_param": "productId",
		"params": {
			"productId": {"represents": "Product", "role": "primary"},
		},
	},
	("/create-site", ":productId", "/login-to-site"): {
		"route": "/create-site/:productId/login-to-site",
		"page": "Signup login to site",
		"primary_param": "productId",
		"params": {
			"productId": {"represents": "Product", "role": "primary"},
		},
	},
	("/impersonate", ":teamId"): {
		"route": "/impersonate/:teamId",
		"page": "Team impersonation",
		"primary_param": "teamId",
		"params": {
			"teamId": {"represents": "Team", "role": "primary"},
		},
	},
	("/install-app", ":app"): {
		"route": "/install-app/:app",
		"page": "Install Marketplace App",
		"primary_param": "app",
		"params": {
			"app": {"represents": "Marketplace App", "role": "primary"},
		},
	},
	("/create-site", ":app"): {
		"route": "/create-site/:app",
		"page": "Create Site for Marketplace App",
		"primary_param": "app",
		"params": {
			"app": {"represents": "Marketplace App", "role": "primary"},
		},
	},
	("/developer-reply", ":marketplaceApp", ":reviewId"): {
		"route": "/developer-reply/:marketplaceApp/:reviewId",
		"page": "Marketplace App review reply",
		"primary_param": "reviewId",
		"params": {
			"marketplaceApp": {"represents": "Marketplace App", "role": "parent"},
			"reviewId": {"represents": "Marketplace App Review", "role": "primary"},
		},
	},
	("/subscription", ":site?"): {
		"route": "/subscription/:site?",
		"page": "Subscription",
		"primary_param": "site",
		"params": {
			"site": {"represents": "Site", "role": "primary"},
		},
	},
	("/setup-account", ":requestKey", ":joinRequest?"): {
		"route": "/setup-account/:requestKey/:joinRequest?",
		"page": "Account setup",
		"primary_param": "requestKey",
		"params": {
			"requestKey": {"represents": "Account setup request key", "role": "primary", "sensitive": True},
			"joinRequest": {"represents": "Join request", "role": "context"},
		},
	},
	("/accept-invite", ":requestKey", ":joinRequest?"): {
		"route": "/accept-invite/:requestKey/:joinRequest?",
		"page": "Team invite setup",
		"primary_param": "requestKey",
		"params": {
			"requestKey": {"represents": "Invite request key", "role": "primary", "sensitive": True},
			"joinRequest": {"represents": "Join request", "role": "context"},
		},
	},
	("/reset-password", ":requestKey"): {
		"route": "/reset-password/:requestKey",
		"page": "Reset password",
		"primary_param": "requestKey",
		"params": {
			"requestKey": {"represents": "Password reset request key", "role": "primary", "sensitive": True},
		},
	},
	("/checkout", ":secretKey"): {
		"route": "/checkout/:secretKey",
		"page": "Checkout",
		"primary_param": "secretKey",
		"params": {
			"secretKey": {"represents": "Checkout secret key", "role": "primary", "sensitive": True},
		},
	},
	("/log-browser", ":mode?", ":docName?", ":logId?"): {
		"route": "/log-browser/:mode?/:docName?/:logId?",
		"page": "Log Browser",
		"primary_param": "logId",
		"params": {
			"mode": {"represents": "Log browser mode", "role": "view"},
			"docName": {"represents": "Document name", "role": "context"},
			"logId": {"represents": "Log id", "role": "primary"},
		},
	},
}


@press_mcp.tool()
@system_manager_only
def explain_dashboard_url(url_or_path: str) -> dict:
	"""Explain what dashboard, desk, or app URL params represent.

	Example: /dashboard/groups/bench-0001/deploys/gi1fh92nfi returns that
	the page is for Deploy Candidate Build gi1fh92nfi under Release Group bench-0001.
	Example: /app/agent-job/hicm507mvi returns that hicm507mvi is an Agent Job.
	"""
	return _explain_dashboard_url(url_or_path)


def _explain_dashboard_url(url_or_path: str) -> dict:
	path = _normalize_path(url_or_path)
	segments = [segment for segment in path.split("/") if segment]
	desk_route = _explain_desk_route(path, segments)
	if desk_route:
		return desk_route

	for pattern, route in sorted(ROUTES.items(), key=_route_sort_key):
		values = _match(pattern, segments)
		if values is None:
			continue

		entities = [
			{
				"param": key,
				"value": _visible_value(value, route["params"][key]),
				"represents": route["params"][key]["represents"],
				"role": route["params"][key]["role"],
				"is_sensitive": bool(route["params"][key].get("sensitive")),
			}
			for key, value in values.items()
		]
		primary_entity = _primary_entity(route, entities)
		return {
			"recognized": True,
			"path": path,
			"dashboard_path": f"{DASHBOARD_PREFIX}{path}",
			"route": route["route"],
			"page": route["page"],
			"meaning": _meaning(route, primary_entity, entities),
			"primary_entity": primary_entity,
			"entities": entities,
		}

	return {
		"recognized": False,
		"path": path,
		"dashboard_path": f"{DASHBOARD_PREFIX}{path}",
		"message": f"Route not recognized: {path}",
	}


def _explain_desk_route(path: str, segments: list[str]) -> dict | None:
	if not segments or segments[0] not in DESK_PREFIXES:
		return None

	if len(segments) < 2:
		return {
			"recognized": False,
			"path": path,
			"dashboard_path": None,
			"message": f"Desk route is missing a DocType slug: {path}",
		}

	if len(segments) > 3:
		return {
			"recognized": False,
			"path": path,
			"dashboard_path": None,
			"message": f"Desk route has too many segments: {path}",
		}

	doctype_slug = unquote(segments[1])
	doctype = DOCTYPE_SLUGS.get(doctype_slug.lower())
	if not doctype:
		return {
			"recognized": False,
			"path": path,
			"dashboard_path": None,
			"message": f"Desk route DocType slug not recognized: {doctype_slug}",
			"entities": [
				{
					"param": "doctype",
					"value": doctype_slug,
					"represents": "DocType slug",
					"role": "context",
					"is_sensitive": False,
				}
			],
		}

	name = unquote(segments[2]) if len(segments) > 2 else None
	entities = [
		{
			"param": "doctype",
			"value": doctype_slug,
			"represents": "DocType slug",
			"role": "context",
			"is_sensitive": False,
		}
	]
	primary_entity = None

	if name:
		primary_entity = {
			"param": "name",
			"value": name,
			"represents": doctype,
			"role": "primary",
			"is_sensitive": False,
		}
		entities.append(primary_entity)

	return {
		"recognized": True,
		"path": path,
		"dashboard_path": None,
		"route": f"/{segments[0]}/:doctype/:name" if name else f"/{segments[0]}/:doctype",
		"page": f"{doctype} desk document" if name else f"{doctype} desk list",
		"meaning": _desk_meaning(doctype, name),
		"primary_entity": primary_entity,
		"entities": entities,
	}


def _desk_meaning(doctype: str, name: str | None) -> str:
	if name:
		return f"This URL points to {doctype} {name}."

	return f"This URL points to the {doctype} list in Desk."


def _route_sort_key(item: tuple[tuple[str, ...], dict]) -> tuple[int, int, int, int]:
	pattern, _route = item
	pattern_segments = [part.strip("/") for part in pattern]
	static_count = sum(1 for segment in pattern_segments if not segment.startswith(":"))
	required_count = sum(1 for segment in pattern_segments if not _is_optional_param(segment))
	optional_count = len(pattern_segments) - required_count

	return (-required_count, -static_count, -len(pattern_segments), optional_count)


def _visible_value(value: str, param: dict) -> str:
	if param.get("sensitive"):
		return "****"

	return value


def _primary_entity(route: dict, entities: list[dict]) -> dict | None:
	return next(
		(entity for entity in entities if entity["param"] == route["primary_param"]),
		next((entity for entity in entities if entity["role"] == "primary"), None),
	)


def _meaning(route: dict, primary_entity: dict | None, entities: list[dict]) -> str:
	if not primary_entity:
		return f"This URL points to the {route['page']} page."

	parent_entity = next((entity for entity in entities if entity["role"] == "parent"), None)
	meaning = f"This URL points to {primary_entity['represents']} {primary_entity['value']}."
	if parent_entity:
		meaning += f" It is shown under {parent_entity['represents']} {parent_entity['value']}."

	return meaning


def _normalize_path(url_or_path: str) -> str:
	path = urlparse(str(url_or_path or "").strip()).path

	if path == DASHBOARD_PREFIX:
		path = "/"
	elif path.startswith(f"{DASHBOARD_PREFIX}/"):
		path = path[len(DASHBOARD_PREFIX) :]

	return "/" + path.strip("/")


def _match(pattern: tuple[str, ...], segments: list[str]) -> dict | None:
	pattern_segments = [part.strip("/") for part in pattern]
	required_segments = [segment for segment in pattern_segments if not _is_optional_param(segment)]
	if len(segments) < len(required_segments) or len(segments) > len(pattern_segments):
		return None

	values = {}
	for index, expected in enumerate(pattern_segments):
		actual = segments[index] if index < len(segments) else None
		if expected.startswith(":"):
			if actual is not None:
				values[expected.removeprefix(":").removesuffix("?")] = unquote(actual)
			elif _is_optional_param(expected):
				continue
			else:
				return None
		elif expected != actual:
			return None

	return values


def _is_optional_param(segment: str) -> bool:
	return segment.startswith(":") and segment.endswith("?")
