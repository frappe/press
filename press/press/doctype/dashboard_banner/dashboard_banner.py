# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class DashboardBanner(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.press.doctype.dashboard_banner_dismissal.dashboard_banner_dismissal import (
			DashboardBannerDismissal,
		)

		action: DF.Data | None
		action_label: DF.Data | None
		enabled: DF.Check
		has_action: DF.Check
		help_url: DF.Data | None
		is_dismissible: DF.Check
		is_global: DF.Check
		is_scheduled: DF.Check
		message: DF.LongText | None
		scheduled_end_time: DF.Datetime | None
		scheduled_start_time: DF.Datetime | None
		server: DF.Link | None
		site: DF.Link | None
		team: DF.Link | None
		title: DF.Data | None
		type: DF.Literal["Info", "Success", "Error", "Warning"]
		type_of_scope: DF.Literal["Team", "Server", "Site"]
		user_dismissals: DF.Table[DashboardBannerDismissal]
	# end: auto-generated types
