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

	def sign(
		self, identity, principals, duration, public_key_path, serial_number, host_key=False
	):
		if principals is None:
			principals = []

		host_flag = "-h " if host_key else ""
		principals_argument = f"-n {','.join(principals)} " if principals else ""
		self.run(
			f"ssh-keygen -s ca -I {identity} {host_flag} {principals_argument}"
			f" -z {serial_number}"
			" -O no-port-forwarding -O no-user-rc -O no-x11-forwarding -O no-agent-forwarding -O permit-pty"
			f" -V {duration}"
			f" {public_key_path}",
			directory=self.directory,
		)

	@property
	def private_key_file(self):
		return os.path.join(self.directory, "ca")

	@property
	def public_key_file(self):
		return os.path.join(self.directory, "ca.pub")

	@property
	def build_directory(self):
		return os.path.join(self.directory, "build")

	@frappe.whitelist()
	def build_image(self):
		frappe.enqueue_doc(self.doctype, self.name, "_build_image", timeout=2400)

	def _build_image(self):
		self._prepare_build_directory()
		self._prepare_build_context()
		self._run_docker_build()
		self._push_docker_image()

	def _prepare_build_directory(self):
		if os.path.exists(self.build_directory):
			shutil.rmtree(self.build_directory)
		os.mkdir(self.build_directory)

	def _prepare_build_context(self):
		for target in ["sshd_config", "Dockerfile"]:
			shutil.copy(
				os.path.join(frappe.get_app_path("press", "docker", "ssh_proxy"), target),
				self.build_directory,
			)

	def _run_docker_build(self):
		environment = os.environ
		environment.update(
			{"DOCKER_BUILDKIT": "1", "BUILDKIT_PROGRESS": "plain", "PROGRESS_NO_TRUNC": "1"}
		)

		settings = frappe.db.get_value(
			"Press Settings",
			None,
			["domain", "docker_registry_url", "docker_registry_namespace"],
			as_dict=True,
		)

		if settings.docker_registry_namespace:
			namespace = f"{settings.docker_registry_namespace}/{settings.domain}"
		else:
			namespace = f"{settings.domain}"

		self.docker_image_repository = f"{settings.docker_registry_url}/{namespace}/ssh"

		self.docker_image_tag = cint(self.docker_image_tag) + 1
		self.docker_image = f"{self.docker_image_repository}:{self.docker_image_tag}"
		self.save()
		frappe.db.commit()

		self.run(f"docker build -t {self.docker_image} .", self.build_directory, environment)

	def _push_docker_image(self):
		settings = frappe.db.get_value(
			"Press Settings",
			None,
			["docker_registry_url", "docker_registry_username", "docker_registry_password"],
			as_dict=True,
		)

		client = docker.from_env()
		client.login(
			registry=settings.docker_registry_url,
			username=settings.docker_registry_username,
			password=settings.docker_registry_password,
		)

		for line in client.images.push(
			self.docker_image_repository, self.docker_image_tag, stream=True, decode=True
		):
			print(line)
