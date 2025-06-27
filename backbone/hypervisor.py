# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt
import platform
import subprocess
from pathlib import Path


class Hypervisor:
	def __init__(self, shell=None):
		self.shell = shell

	def setup(self):
		system = platform.system()
		if system == "Linux":
			self.preinstall()
			self.install()
			self.verify()
		elif system == "Darwin":
			self.verify_mac()

	def build(self, size):
		system = platform.system()
		if system == "Linux":
			self.build_cloud_init_linux()
		elif system == "Darwin":
			self.build_cloud_init_mac()
		self.build_packer("backbone", size=size)

	def build_cloud_init_linux(self):
		cloud_init_yml = str(Path(__file__).parent.joinpath("packer", "cloud-init.yml"))
		cloud_init_image = str(Path(__file__).parent.joinpath("packer", "cloud-init.img"))
		self.shell.execute(f"cloud-localds {cloud_init_image} {cloud_init_yml}")

	def build_cloud_init_mac(self):
		# cloud-localds isn't available on macOS.
		# So we do what it does ourselves
		# user-data is the same as cloud-init.yml
		# https://github.com/canonical/cloud-utils/blob/49e5dd7849ee3c662f3db35e857148d02e72694b/bin/cloud-localds#L168-L187
		cloud_init_yml = str(Path(__file__).parent.joinpath("packer", "cloud-init.yml"))
		user_data = str(Path(__file__).parent.joinpath("packer", "user-data"))
		self.shell.execute(f"cp {cloud_init_yml} {user_data}")

		# meta-data has some inconsequential values
		# but the file is needed
		meta_data = str(Path(__file__).parent.joinpath("packer", "meta-data"))
		self.shell.execute(f"touch {meta_data}")

		cloud_init_image = str(Path(__file__).parent.joinpath("packer", "cloud-init.img"))
		# Reference: https://github.com/canonical/cloud-utils/blob/49e5dd7849ee3c662f3db35e857148d02e72694b/bin/cloud-localds#L235-L237
		self.shell.execute(
			f"mkisofs -joliet -rock -volid cidata -output {cloud_init_image} {user_data} {meta_data}"
		)

	def build_packer(self, template, size):
		packer_template = str(Path(__file__).parent.joinpath("packer", f"{template}.json"))
		packer = self.shell.execute(f"packer build -var 'disk_size={size}' {packer_template}")
		if packer.returncode:
			raise Exception("Build Failed")

		box = str(Path(__file__).parent.joinpath("packer", "builds", f"{template}.box"))
		add = self.shell.execute(f"vagrant box add {box} --name {template} --force")
		if add.returncode:
			raise Exception(f"Cannot add box {box}")

	def build_scaleway(self, size):
		self.build_cloud_init_scaleway()
		self.build_packer("scaleway", size=size)

	def build_cloud_init_scaleway(self):
		cloud_init_yml = str(Path(__file__).parent.joinpath("packer", "cloud-init-scaleway.yml"))

		cloud_init_image = str(Path(__file__).parent.joinpath("packer", "cloud-init-scaleway.img"))
		self.shell.execute(f"cloud-localds {cloud_init_image} {cloud_init_yml}")

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

	def verify_mac(self):
		kvm_connect = self.shell.execute("virsh list --all")
		if kvm_connect.returncode:
			raise Exception("Cannot connect to KVM")


class Shell:
	def __init__(self, directory=None):
		self.directory = directory

	def execute(self, command, directory=None):
		directory = directory or self.directory
		return subprocess.run(
			command, check=False, stderr=subprocess.STDOUT, cwd=directory, shell=True, text=True
		)
