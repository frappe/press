import sys

from backbone.hypervisor import Shell

shell = Shell()


def apt_install(packages):
	shell.execute(
		f"sudo apt install --yes --no-install-suggests --no-install-recommends {packages}"
	)


def main(args):
	prepare()
	setup_vagrant()
	setup_kvm()
	setup_libvirt()
	setup_packer()


def prepare():
	shell.execute("sudo apt update")
	apt_install("build-essential")


def setup_vagrant():
	VAGRANT_SERVER = "https://releases.hashicorp.com/vagrant/2.2.10"
	VAGRANT_PACKAGE = "vagrant_2.2.10_x86_64.deb"
	shell.execute(f"wget {VAGRANT_SERVER}/{VAGRANT_PACKAGE} -O {VAGRANT_PACKAGE}")
	shell.execute(f"sudo dpkg -i {VAGRANT_PACKAGE}")


def setup_packer():
	PACKER_KEY = "https://apt.releases.hashicorp.com/gpg"
	PACKER_REPO = (
		'"deb [arch=amd64] https://apt.releases.hashicorp.com $(lsb_release -cs) main"'
	)
	shell.execute(f"curl -fsSL {PACKER_KEY} | sudo apt-key add -")
	shell.execute(f"sudo apt-add-repository {PACKER_REPO}")
	apt_install("packer cloud-utils")


def setup_kvm():
	apt_install("qemu-kvm")
	shell.execute("sudo usermod -aG kvm $USER")


def setup_libvirt():
	apt_install("libvirt-dev libvirt-daemon-system qemu-utils dnsmasq-base")
	shell.execute("sudo usermod -aG libvirt $USER")
	shell.execute("vagrant plugin install vagrant-libvirt")
	shell.execute("vagrant plugin install vagrant-hostmanager")


if __name__ == "__main__":
	sys.exit(main(sys.argv))
