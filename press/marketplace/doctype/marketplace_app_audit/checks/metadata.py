import json
import re

import frappe

from press.marketplace.doctype.marketplace_app_audit.marketplace_app_audit import CheckResult

# Summary of checks present in metadata.py with their respective severity levels:
# - long description checks: Major
# - screenshots: Major
# - links: Major
# - categories: Minor

CATEGORY = "Metadata"

# Patterns that indicate the publisher used bench install instructions which are not relevant on FC Listing.
INSTALL_INSTRUCTION_PATTERNS = [
	r"bench\s+get-app",
	r"bench\s+install-app",
	r"bench\s+--site\s+\S+\s+install-app",
	r"bench\s+setup",
	r"git\s+clone",
	r"bench\s+new-site",
	r"bench\s+start",
	r"bench\s+migrate",
]


def run_metadata_checks(marketplace_app) -> list[CheckResult]:
	"""
	Run all the metadata checks for the given marketplace app.
	By meta data checks - we basically check the hygiene on any marketplace app.
	Checks consist of:
	- App Name, Descriptions(Short and Long), Logo, Screenshots, Categories, Support Links.
	"""
	results = []
	results.append(check_long_description(marketplace_app))
	results.append(check_screenshots(marketplace_app))
	results.append(check_links(marketplace_app))
	results.append(check_categories(marketplace_app))
	return results


def check_long_description(marketplace_app):
	"""
	Check the long description of the given marketplace app.
	Ideally the long description should consist of the following sections:
	- Overview: a short description of the app.
	- Features: a list of features of the app.
	- Usage: a guide to use the app.
	- Support: some sort of support information for the app.
	- FAQ: a list of frequently asked questions about the app. ? Optional
	- License: the license of the app. ? Optional maybe because we ensure that the apps published are open source.

	Should Not Contain:
	- Installation: As this is not relevant for the marketplace app on FC. Anything related to "bench get-app", "bench install-app", etc. should be removed.
	- Architecture: the architecture of the app. As this is not relevant for the marketplace app on FC.
	- Contribution Guidelines: As this is not relevant for the marketplace app on FC.(Github info)
	- Other Links: As all the links are provided in the Support Links section.

	We should only check for negative cases here.

	"""
	long_description = (marketplace_app.long_description).strip()
	plain_text = frappe.core.utils.html2text(long_description)

	check_id = "meta_long_description_checks"
	severity = "Major"

	# Check 1: if the long description is missing
	if not plain_text:
		return CheckResult(
			check_id,
			check_name="Missing Long Description",
			category=CATEGORY,
			severity=severity,
			result="Fail",
			message="Long description is missing. Please add a long description for the marketplace app.",
			details="The long description is missing for the marketplace app.",
			remediation="Please add a long description for the marketplace app.",
		)

	# Check 2: Check if the long description contains any of the install instruction patterns

	# firstly convert the long description to plain text as the field is of Rich Text Editor.
	# frappe.utils.html2text returns markdown text.
	found_patterns = []
	for pattern in INSTALL_INSTRUCTION_PATTERNS:
		if re.search(pattern, plain_text):
			found_patterns.append(pattern)

	if found_patterns:
		return CheckResult(
			check_id,
			check_name="Long Description Contains Install Instructions",
			category=CATEGORY,
			severity=severity,
			result="Warn",
			message="Long description contains install instructions. Please don't add any installation instructions in the description.",
			details=json.dumps(
				{
					"found_patterns": found_patterns,
				}
			),
			remediation="Please remove any installation instructions from the description.",
		)

	# TODO: Check 3: Check if there are any Architecture/Deployment related information in the long description.

	# Check 4: Check that there are not any other links in the long description. All links are anyhow provided in the Support Links section.
	if re.search(r"https?://\S+", plain_text):
		return CheckResult(
			check_id,
			check_name="Long Description Contains Other Links",
			category=CATEGORY,
			severity=severity,
			result="Warn",
			message="Long description contains other links. Please don't add any other links in the description.",
			remediation="Please remove any other links from the description.",
		)

	# Success Case:
	return CheckResult(
		check_id,
		check_name="Long Description Checks",
		category=CATEGORY,
		severity=severity,
		result="Pass",
		message="Long description checks passed.",
		# no need to provide any details or remediation as all the checks passed.
	)


def check_screenshots(marketplace_app):
	"""
	For now, we will just check if the screenshots are present.

	Eventually add dimensions, aspect ratio checks etc.
	"""
	screenshots = marketplace_app.screenshots
	check_id = "meta_screenshots_checks"
	severity = "Major"

	if len(screenshots) == 0:
		return CheckResult(
			check_id,
			check_name="No Screenshots",
			category=CATEGORY,
			severity=severity,
			result="Fail",
			message="No screenshots are present for the marketplace app.",
			remediation="Please add screenshots for the marketplace app.",
		)

	return CheckResult(
		check_id,
		check_name="Screenshots Checks",
		category=CATEGORY,
		severity=severity,
		result="Pass",
		message="Screenshots checks passed.",
	)


def check_links(marketplace_app):
	"""
	Links should be present and not broken as well.
	"""
	import requests

	website = marketplace_app.website
	support = marketplace_app.support
	documentation = marketplace_app.documentation
	privacy_policy = marketplace_app.privacy_policy
	terms_of_service = marketplace_app.terms_of_service

	link_labels = {
		"website": "Website",
		"support": "Support",
		"documentation": "Documentation",
		"privacy_policy": "Privacy Policy",
		"terms_of_service": "Terms of Service",
	}

	check_id = "meta_links_checks"
	severity = "Major"
	# Check 1: Check if any of the links are missing
	if any(
		link is None or link == ""
		for link in [website, support, documentation, privacy_policy, terms_of_service]
	):
		return CheckResult(
			check_id,
			check_name="Missing Links",
			category=CATEGORY,
			severity=severity,
			result="Fail",
			message="This app is missing some important links. Please add the missing links for the app to be published on FC.",
			details=json.dumps(
				{
					"missing_links": [
						link_labels.get(link) for link in link_labels if link is None or link == ""
					],
				}
			),
			remediation="Please add the missing links for the app.",
		)

	# Check 2: Check if the links are broken
	broken_links = []
	for link in [website, support, documentation, privacy_policy, terms_of_service]:
		try:
			# add timeout to the request to avoid hanging requests(timeout = (connect timeout, read timeout))
			response = requests.get(link, timeout=(3, 10))
			# 0k or redirect is fine.
			if response.status_code not in [200, 301, 302]:
				broken_links.append(link)
		except requests.exceptions.RequestException:
			broken_links.append(link)

	if broken_links:
		return CheckResult(
			check_id,
			check_name="Broken Links",
			category=CATEGORY,
			severity=severity,
			result="Fail",
			message="This app has some broken links. Please fix the broken links for the app to be published on FC.",
			details=json.dumps(
				{
					"broken_links": broken_links,
				}
			),
			remediation="Please fix the broken links for the app.",
		)

	# Success Case:
	return CheckResult(
		check_id,
		check_name="Links Checks",
		category=CATEGORY,
		severity=severity,
		result="Pass",
		message="Links checks passed.",
	)


def check_categories(marketplace_app):
	"""
	Categories are not always provided by the publisher. The reviewer should check if the categories are present.
	If not, the reviewer should add the categories once approving the app.
	TODO: Also need to check if the app belongs to the categories(relevance)
	"""

	categories = marketplace_app.categories
	check_id = "meta_categories_checks"
	severity = "Minor"

	if len(categories) == 0:
		return CheckResult(
			check_id,
			check_name="No Categories",
			category=CATEGORY,
			severity=severity,
			result="Warn",
			message="No categories are present for the app. Please add relevant categories for the app",
			remediation="Please add relevant categories for the app.",
		)

	return CheckResult(
		check_id,
		check_name="Categories Checks",
		category=CATEGORY,
		severity=severity,
		result="Pass",
		message="Categories checks passed.",
	)
