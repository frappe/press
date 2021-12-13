# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import base64
import binascii
import hashlib
from press.utils import log_error
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

	def before_insert(self):
		if frappe.get_all(
			"User SSH Certificate",
			{
				"user": self.user,
				"valid_until": [">", frappe.utils.now()],
				"access_server": self.access_server,
				"all_servers": self.all_servers,
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

		tmp_pub_file_prefix = f"/tmp/id_{self.key_type}-{self.name}"
		tmp_pub_file = tmp_pub_file_prefix + ".pub"
		# write the public key to a /tmp file
		with open(tmp_pub_file, "w") as public_key:
			public_key.write(self.ssh_public_key)
			public_key.flush()

		if self.all_servers:
			principal = "all-servers"
		else:
			principal = self.access_server

		# try generating a certificate for the /tmp key.
		try:
			command = (
				f"ssh-keygen -s ca -I {self.name} -n {principal} -V +{self.validity} {tmp_pub_file}"
			)
			subprocess.check_output(shlex.split(command), cwd="/etc/ssh")
		except subprocess.CalledProcessError as e:
			log_error("SSH Certificate Generation Error", exception=e)
			frappe.throw(
				"Failed to generate a certificate for the specified key. Please try again."
			)
		process = subprocess.Popen(
			shlex.split(f"ssh-keygen -Lf {tmp_pub_file_prefix}-cert.pub"),
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


@frappe.whitelist()
def get_ssh_command(docname):
	ssh_port = 22
	ssh_user = "frappe"
	certificate = frappe.get_doc("User SSH Certificate", docname)
	server = certificate.access_server

	if certificate.ssh_command:
		return certificate.ssh_command

	return f"ssh {server} -p {ssh_port} -l {ssh_user}"


def set_user_ssh_key(user, ssh_public_key):
	frappe.db.set_value("User", user, "ssh_public_key", ssh_public_key)
