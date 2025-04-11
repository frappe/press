# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt


# This provides stop and fail support since docmethod does not take worker changes into account.

import typing

import frappe

if typing.TYPE_CHECKING:
	from press.press.doctype.deploy_candidate_build.deploy_candidate_build import DeployCandidateBuild


@frappe.whitelist()
def stop_and_fail(dn: str):
	build: DeployCandidateBuild = frappe.get_doc("Deploy Candidate Build", dn, for_update=True)

	if build.status in ["Running", "Preparing", "Pending"]:
		build._stop_and_fail()
