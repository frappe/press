# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt


# import frappe
from frappe.model.document import Document


class RemoteOperationLog(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		operation_type: DF.Literal["Delete Files"]
		response: DF.Code
	# end: auto-generated types

	pass
