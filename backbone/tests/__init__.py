# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt
import unittest
from pathlib import Path

from coverage import Coverage


def run_tests():
	coverage = Coverage(
		source=[str(Path(__file__).parent.parent)], omit=["*/tests/*"], branch=True
	)
	coverage.start()
	unittest.main(module=None, argv=["", "discover", "-s", "backbone"], exit=False)
	coverage.stop()
	coverage.save()
	coverage.html_report()


if __name__ == "__main__":
	unittest.main()
