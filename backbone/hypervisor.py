# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt
import subprocess
from pathlib import Path


class Hypervisor:
	def __init__(self, shell=None):
		self.shell = shell

	def setup(self):
		self.preinstall()
		self.install()
		self.verify()

	def build(self, size):
		cloud_init_yml = str(Path(__file__).parent.joinpath("packer", "cloud-init.yml"))
		cloud_init_image = str(Path(__file__).parent.joinpath("packer", "cloud-init.img"))
		self.shell.execute(f"cloud-localds {cloud_init_image} {cloud_init_yml}")

		packer_template = str(Path(__file__).parent.joinpath("packer", "backbone.json"))
		packer = self.shell.execute(f"packer build -var 'disk_size={size}' {packer_template}")
		if packer.returncode:
			raise Exception("Build Failed")

		box = str(Path(__file__).parent.joinpath("packer", "builds", "backbone.box"))
		add = self.shell.execute(f"vagrant box add {box} --name backbone --force")
		if add.returncode:
			raise Exception(f"Cannot add box {box}")

	def build_scaleway(self, size):
		cloud_init_yml = str(
			Path(__file__).parent.joinpath("packer", "cloud-init-scaleway.yml")
		)
		cloud_init_image = str(
			Path(__file__).parent.joinpath("packer", "cloud-init-scaleway.img")
		)
		self.shell.execute(f"cloud-localds {cloud_init_image} {cloud_init_yml}")

		packer_template = str(Path(__file__).parent.joinpath("packer", "scaleway.json"))
		packer = self.shell.execute(f"packer build -var 'disk_size={size}' {packer_template}")
		if packer.returncode:
			raise Exception("Build Failed")

		box = str(Path(__file__).parent.joinpath("packer", "builds", "scaleway.box"))
		add = self.shell.execute(f"vagrant box add {box} --name scaleway --force")
		if add.returncode:
			raise Exception(f"Cannot add box {box}")

	def up(self):
		vagrant = self.shell.execute("vagrant init backbone")
		vagrant = self.shell.execute("vagrant up --provider=libvirt")
		if vagrant.returncode:
			raise Exception("Cannot start hypervisor")

	def ssh(self, command=None):
		if command:
			vagrant = self.shell.execute(f'vagrant ssh -c "{command}"')
		else:
			vagrant = self.shell.execute("vagrant ssh")
		if vagrant.returncode:
			raise Exception("Cannot ssh")

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
			command, check=False, stderr=subprocess.STDOUT, cwd=directory, shell=True, text=True
		)
		return process
