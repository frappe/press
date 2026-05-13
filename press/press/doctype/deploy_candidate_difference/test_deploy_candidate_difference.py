# Copyright (c) 2020, Frappe and Contributors
# See license.txt


from unittest.mock import Mock, patch

from frappe.tests.utils import FrappeTestCase

from press.press.doctype.deploy.deploy import create_deploy_candidate_differences


@patch("press.press.doctype.deploy.deploy.frappe.db.commit", new=Mock())
def create_test_deploy_candidate_differences(*args, **kwargs):
	return create_deploy_candidate_differences(*args, **kwargs)


class TestDeployCandidateDifference(FrappeTestCase):
	pass
