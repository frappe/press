# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import time

from frappe.tests.utils import FrappeTestCase

from press.utils import cache, now


class TestCache(FrappeTestCase):
	"""The TTL cache in `press.utils.cache`.

	Its expiry bookkeeping used `datetime.utcnow()`, which is removed in Python
	3.15. Both sides of the comparison were naive, so switching to aware UTC is
	behaviour-preserving.
	"""

	def test_now_is_timezone_aware_utc(self):
		self.assertIsNotNone(now().tzinfo)
		self.assertEqual(now().utcoffset().total_seconds(), 0)

	def test_result_is_cached_within_the_ttl(self):
		calls = []

		@cache(seconds=60)
		def counted():
			calls.append(1)
			return len(calls)

		self.assertEqual(counted(), 1)
		self.assertEqual(counted(), 1)
		self.assertEqual(len(calls), 1)

	def test_cache_clears_once_the_ttl_passes(self):
		calls = []

		@cache(seconds=1)
		def counted():
			calls.append(1)
			return len(calls)

		self.assertEqual(counted(), 1)
		time.sleep(1.1)
		self.assertEqual(counted(), 2)
		self.assertEqual(len(calls), 2)

	def test_expiration_is_aware(self):
		"""Naive and aware cannot be compared, so this must not drift back."""

		@cache(seconds=60)
		def noop():
			return 1

		self.assertIsNotNone(noop.expiration.tzinfo)
		# The comparison inside the wrapper is what would raise if one side
		# were naive and the other aware.
		self.assertIsInstance(now() >= noop.expiration - noop.delta, bool)
