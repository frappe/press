# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals


import os
import shlex
import shutil
import subprocess

from frappe.model.document import Document


class SSHCertificateAuthority(Document):
	def after_insert(self):
		self.setup_directory()
		self.generate_key_pair()
		self.extract_public_key()
		self.extract_key_fingerprint()

	def setup_directory(self):
		os.mkdir(self.directory)

	def run(self, command, directory, environment=None):
		return subprocess.check_output(
			shlex.split(command), cwd=directory, env=environment
		).decode()

	def generate_key_pair(self):
		self.run("ssh-keygen -C ca -t rsa -b 4096 -f ca -N ''", directory=self.directory)
		os.chmod(self.public_key_file, 0o400)
		os.chmod(self.private_key_file, 0o400)

	def extract_public_key(self):
		with open(self.public_key_file) as f:
			self.public_key = f.read()

	def extract_key_fingerprint(self):
		self.key_fingerprint = self.run("ssh-keygen -l -f ca.pub", directory=self.directory)

	def on_trash(self):
		if os.path.exists(self.directory):
			shutil.rmtree(self.directory)

	@property
	def private_key_file(self):
		return os.path.join(self.directory, "ca")

	@property
	def public_key_file(self):
		return os.path.join(self.directory, "ca.pub")
