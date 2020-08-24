# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt
import subprocess


class Hypervisor:
	def __init__(self, shell=None):
		self.shell = shell

	def setup(self):
		self.preinstall()
		self.install()
		self.verify()

	def preinstall(self):
		kvm_ok = self.shell.execute("kvm-ok")
		if kvm_ok.returncode:
			raise Exception("Cannot use KVM")

	def install(self):
		kvm_install = self.shell.execute("sudo apt install qemu-kvm")
		if kvm_install.returncode:
			raise Exception("Cannot install KVM")

	def verify(self):
		kvm_connect = self.shell.execute("virsh list --all")
		if kvm_connect.returncode:
			raise Exception("Cannot connect to KVM")


class Shell:
	def __init__(self, directory=None):
		self.directory = directory

	def execute(self, command, directory=None):
		directory = directory or self.directory
		process = subprocess.run(
			command,
			check=False,
			stdout=subprocess.PIPE,
			stderr=subprocess.STDOUT,
			cwd=directory,
			shell=True,
			text=True,
		)
		return process
