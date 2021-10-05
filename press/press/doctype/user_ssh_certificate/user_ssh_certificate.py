# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import base64
import binascii
import hashlib
import re
import shlex
import subprocess

import frappe
from frappe import safe_decode
from frappe.model.document import Document


class UserSSHCertificate(Document):
	def validate(self):
		if not self.ssh_public_key:
			frappe.throw("Please make sure that a valid public key has been added in team doc.")

		# check if the ssh key is valid
		try:
			base64.b64decode(self.ssh_public_key.strip().split()[1])
		except binascii.Error:
			frappe.throw("Please ensure that the attached text is a valid public key")

		# check if there is an existing valid certificate for the server
		if frappe.get_all(
			"User SSH Certificate",
			{
				"team": self.team,
				"valid_until": [">", frappe.utils.now()],
				"access_server": self.access_server,
				"docstatus": 1,
			},
		):
			frappe.throw("A valid certificate already exists.")

	def before_save(self):
		# decode the ssh key and generate a fingerprint
		ssh_key = self.ssh_public_key.strip().split()[1]
		ssh_key_b64 = base64.b64decode(ssh_key)
		sha256_sum = hashlib.sha256()
		sha256_sum.update(ssh_key_b64)
		self.ssh_fingerprint = safe_decode(base64.b64encode(sha256_sum.digest()))

	def before_submit(self):
		# extract key_type (eg: rsa, ecdsa, ed25519.) for naming convention
		self.key_type = self.ssh_public_key.strip().split()[0].split("-")[1]
		if not self.key_type:
			frappe.throw("Could not guess the key type. Please check your public key.")

		# write the public key to a /tmp file
		with open(f"/tmp/id_{self.key_type}-{self.name}.pub", "w") as public_key:
			public_key.write(self.ssh_public_key)
			public_key.flush()

		principal = self.access_server

		# try generating a certificate for the /tmp key.
		try:
			command = (
				f"ssh-keygen -s ca -I {self.name} -n {principal} -V +{self.validity}"
				f" /tmp/id_{self.key_type}-{self.name}.pub"
			)
			subprocess.check_output(shlex.split(command), cwd="/etc/ssh")
		except subprocess.CalledProcessError:
			frappe.throw(
				"Failed to generate a certificate for the specified key. Please try again."
			)
		process = subprocess.Popen(
			shlex.split(f"ssh-keygen -Lf /tmp/id_{self.key_type}-{self.name}-cert.pub"),
			stdout=subprocess.PIPE,
		)
		self.certificate_details = safe_decode(process.communicate()[0])
		# extract the time for until when the key is active
		regex = re.compile("Valid:.*\n")
		self.valid_until = regex.findall(self.certificate_details)[0].strip().split()[-1]
		self.ssh_certificate = read_certificate(self.key_type, self.name)
		self.ssh_command = get_ssh_command(self.name)

	def before_cancel(self):
		self.delete_key("ssh_certificate")


@frappe.whitelist()
def read_certificate(key_type, docname):
	with open("/tmp/id_{0}-{1}-cert.pub".format(key_type, docname)) as certificate:
		try:
			return certificate.read()
		except Exception:
			pass

		return


@frappe.whitelist()
def get_ssh_command(docname):
	ssh_port = 22
	ssh_user = "frappe"
	certificate_doc = frappe.get_doc("User SSH Certificate", docname)

	if certificate_doc.ssh_command:
		return certificate_doc.ssh_command

	if not certificate_doc.from_doctype == "Self Hosted Service":
		# the default port that we use at frappe is 2332
		ssh_port = 2332
		server = certificate_doc.access_server
	else:
		server_url, ip_address, server_port, server_user = frappe.db.get_value(
			"Self Hosted Service",
			certificate_doc.access_server,
			["server_url", "ip_address", "ssh_port", "ssh_username"],
		)
		server = server_url if server_url else ip_address
		ssh_port = server_port if server_port else ssh_port
		ssh_user = server_user if server_user else ssh_user

	ssh_command = "ssh {server} -p {ssh_port} -l {ssh_user}".format(
		server=server, ssh_port=ssh_port, ssh_user=ssh_user
	)

	return ssh_command


def set_user_ssh_key(user, ssh_public_key):
	frappe.db.set_value("User", user, "ssh_public_key", ssh_public_key)
