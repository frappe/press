# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and Contributors
# License: MIT. See LICENSE

from frappe.tests.utils import FrappeTestCase

from press.utils.db_optimizer import DBOptimizer


class TestDBOptimizer(FrappeTestCase):
	def test_basic_index_existence_analysis(self):
		def possible_indexes(q):
			return DBOptimizer(query=q).potential_indexes

		self.assertEqual(
			["modified"],
			possible_indexes("select `name` from `tabUser` order by `modified` desc limit 1"),
		)

		self.assertEqual(
			["full_name"],
			possible_indexes("select `name` from `tabUser` where full_name = 'xyz'"),
		)

		self.assertIn(
			"tabHasRole.parent",
			possible_indexes(
				"select `name` from `tabUser` u join tabHasRole h on h.parent = u.name"
			),
		)
