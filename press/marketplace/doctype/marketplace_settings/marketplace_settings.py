# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class MarketplaceSettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.marketplace.doctype.auto_release_team.auto_release_team import AutoReleaseTeam
		from press.marketplace.doctype.featured_app.featured_app import FeaturedApp

		audit_bench_path: DF.Data | None
		auto_release_apps: DF.Table[FeaturedApp]
		auto_release_teams: DF.Table[AutoReleaseTeam]
		enable_audit_actions: DF.Check
		featured_apps: DF.Table[FeaturedApp]
		send_report_to_reviewer: DF.Check
	# end: auto-generated types

	pass
