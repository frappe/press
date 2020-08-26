# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt
import unittest
from unittest.mock import MagicMock

from backbone.hypervisor import Hypervisor


class TestHypervisor(unittest.TestCase):
	def test_preinstall_pass(self):
		shell = MagicMock()
		shell.execute.return_value.returncode = 0
		hypervisor = Hypervisor(shell=shell)
		self.assertEqual(hypervisor.preinstall(), None)
		shell.execute.assert_called_with("kvm-ok")

	def test_preinstall_fail(self):
		shell = MagicMock()
		shell.execute.return_value.returncode = 1
		hypervisor = Hypervisor(shell=shell)
		self.assertRaisesRegex(Exception, "Cannot use KVM", hypervisor.preinstall)

	def test_install_pass(self):
		shell = MagicMock()
		shell.execute.return_value.returncode = 0
		hypervisor = Hypervisor(shell=shell)
		self.assertEqual(hypervisor.install(), None)
		shell.execute.assert_called_with("sudo apt install qemu-kvm")

	def test_install_fail(self):
		shell = MagicMock()
		shell.execute.return_value.returncode = 1
		hypervisor = Hypervisor(shell=shell)
		self.assertRaisesRegex(Exception, "Cannot install KVM", hypervisor.install)

	def test_verify_pass(self):
		shell = MagicMock()
		shell.execute.return_value.returncode = 0
		hypervisor = Hypervisor(shell=shell)
		self.assertEqual(hypervisor.verify(), None)
		shell.execute.assert_called_with("virsh list --all")

	def test_verify_fail(self):
		shell = MagicMock()
		shell.execute.return_value.returncode = 1
		hypervisor = Hypervisor(shell=shell)
		self.assertRaisesRegex(Exception, "Cannot connect to KVM", hypervisor.verify)
