# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from datetime import datetime

date_format = '%Y-%m-%d'

def get_formated_date(timestamp):
	return datetime.fromtimestamp(timestamp).strftime(date_format)