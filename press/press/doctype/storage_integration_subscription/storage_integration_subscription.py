# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

import json
import frappe
from hashlib import blake2b
from press.agent import Agent
from frappe.model.document import Document


class StorageIntegrationSubscription(Document):
	pass