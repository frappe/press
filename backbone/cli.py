# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt
import click

from backbone.tests import run_tests


@click.group()
def cli():
	pass


@cli.command()
def tests():
	run_tests()
