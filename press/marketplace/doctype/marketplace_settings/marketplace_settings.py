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

		auto_release_apps: DF.Table[FeaturedApp]
		auto_release_teams: DF.Table[AutoReleaseTeam]
		email: DF.Data | None
		enable_payout_reminder: DF.Check
		featured_apps: DF.Table[FeaturedApp]
	# end: auto-generated types

	pass
