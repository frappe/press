import sys

from backbone.hypervisor import Shell

shell = Shell()


def brew_install(packages):
	shell.execute(f"brew install {packages}")


def main(args):
	prepare()
	setup_qemu()
	setup_vagrant()
	setup_libvirt()
	setup_packer()


def prepare():
	shell.execute("brew update")
	brew_install("cdrtools iproute2mac")


def setup_qemu():
	brew_install("qemu")
	# We might need to disable a few things
	# echo 'security_driver = "none"' >> /opt/homebrew/etc/libvirt/qemu.conf
	# echo "dynamic_ownership = 0" >> /opt/homebrew/etc/libvirt/qemu.conf
	# echo "remember_owner = 0" >> /opt/homebrew/etc/libvirt/qemu.conf


def setup_vagrant():
	# At the time of writing hashicorp tap has older 2.4.2 version
	# We need 2.4.3
	# Reference: https://github.com/vagrant-libvirt/vagrant-libvirt/issues/1831
	brew_install("vagrant")


def setup_libvirt():
	brew_install("libvirt")
	shell.execute("brew services start libvirt")
	# Make sure you haven't installed macports
	# It overrides pkg-config, and we won't find brew libvirt packages
	shell.execute("vagrant plugin install vagrant-libvirt")
	shell.execute("vagrant plugin install vagrant-hostmanager")


def setup_packer():
	shell.execute("brew tap hashicorp/tap")
	brew_install("hashicorp/tap/packer")
	shell.execute("packer plugins install github.com/hashicorp/qemu")
	shell.execute("packer plugins install github.com/hashicorp/vagrant")


if __name__ == "__main__":
	sys.exit(main(sys.argv))
