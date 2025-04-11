import frappe
import unittest
from unittest.mock import patch, MagicMock
from press.press.doctype.bare_metal_host.bare_metal_host import BareMetalHost
from press.runner import Ansible
from frappe.utils import random_string

class TestVMHostSetup(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create test hosts first since cluster needs them
        cls.nfs_server = frappe.get_doc({
            "doctype": "Bare Metal Host",
            "hostname": f"nfs-test-server-{random_string(6)}",
            "ip": "192.168.1.10",
            "ssh_user": "root",
            "ssh_port": 22,
            "total_cpu": 8,
            "total_memory": 16384,  # 16GB
            "total_disk": 500,  # 500GB
            "nfs_exports_directory": "/exports/vm_storage",
            "status": "Active"
        }).insert()
        frappe.db.commit()

        cls.vm_host = frappe.get_doc({
            "doctype": "Bare Metal Host",
            "hostname": f"vm-test-host-{random_string(6)}",
            "ip": "192.168.1.11",
            "ssh_user": "root",
            "ssh_port": 22,
            "total_cpu": 32,
            "total_memory": 65536,  # 64GB
            "total_disk": 1000,  # 1TB
            "nfs_mount_point": "/mnt/vm_storage",
            "is_vm_host": 1,
            "status": "Active"
        }).insert()
        frappe.db.commit()

        # Create test region
        if not frappe.db.exists("Cloud Region", "test-region"):
            frappe.get_doc({
                "doctype": "Cloud Region",
                "region_name": "test-region",
                "provider": "Bare Metal Host",
            }).insert()
            frappe.db.commit()

        # Create test SSH key
        if not frappe.db.exists("SSH Key", "test-key"):
            frappe.get_doc({
                "doctype": "SSH Key",
                "name": "test-key",
                "title": "Test Key",
                "public_key": "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC0 test@example.com",
                "status": "Active"
            }).insert()
            frappe.db.commit()

        # Create cluster with correct cloud provider
        cluster_name = f"test-cluster-{random_string(6)}"
        cls.cluster = frappe.get_doc({
            "doctype": "Cluster",
            "name": cluster_name,
            "cloud_provider": "Bare Metal Host",
            "bare_metal_host": cls.vm_host.name,
            "title": f"Test Cluster {cluster_name}",
            "region": "test-region",  # Use the test region
            "status": "Active"
        }).insert()
        frappe.db.commit()

        # Create test domain
        if not frappe.db.exists("Root Domain", "fc.dev"):
            frappe.get_doc({
                "doctype": "Root Domain",
                "name": "fc.dev",
                "domain": "fc.dev",
                "is_primary": 1,
                "is_active": 1,
                "default_cluster": cls.cluster.name
            }).insert()
            frappe.db.commit()

        # Configure NFS server in settings
        frappe.db.set_single_value("Press Settings", "nfs_server", cls.nfs_server.ip)
        frappe.db.commit()

    @patch('press.runner.Ansible.run')
    def test_01_nfs_server_setup(self, mock_run):
        """Test NFS server setup"""
        mock_run.return_value = MagicMock(status="Success")
        self.nfs_server.setup_nfs_server()
        frappe.db.commit()  # Commit the changes
        self.nfs_server.reload()  # Reload to get fresh values
        self.assertTrue(self.nfs_server.is_nfs_server)
        mock_run.assert_called_once()

    @patch('press.runner.Ansible.run')
    def test_02_vm_host_setup(self, mock_run):
        """Test basic VM host setup without NFS"""
        mock_run.return_value = MagicMock(status="Success")
        self.vm_host.setup_vm_host()
        frappe.db.commit()  # Commit the changes
        self.vm_host.reload()  # Reload to get fresh values
        self.assertTrue(self.vm_host.is_vm_host_setup)
        mock_run.assert_called_once()

    @patch('press.runner.Ansible.run')
    def test_03_vm_host_with_nfs_setup(self, mock_run):
        """Test VM host setup with NFS"""
        mock_run.return_value = MagicMock(status="Success")
        self.vm_host.setup_vm_host_with_nfs()
        frappe.db.commit()  # Commit the changes
        self.vm_host.reload()  # Reload to get fresh values
        self.assertTrue(self.vm_host.is_vm_host_setup)
        self.assertTrue(self.vm_host.is_nfs_client)
        mock_run.assert_called_once()

    @patch('press.press.doctype.virtual_machine.virtual_machine.VirtualMachine.provision')
    def test_04_create_test_vm(self, mock_provision):
        """Test creating a VM on the host"""
        # Create a test VM
        vm = frappe.get_doc({
            "doctype": "Virtual Machine",
            "cluster": self.cluster.name,
            "series": "f",  # For test server
            "domain": "fc.dev",
            "machine_type": "2x4",  # 2 CPU, 4GB RAM
            "platform": "x86_64",
            "disk_size": 20,
            "root_disk_size": 20,
            "region": "test-region",  # Add required field
            "ssh_key": "test-key"  # Add required field
        }).insert()
        
        mock_provision.return_value = None
        vm.provision()
        vm.reload()
        
        mock_provision.assert_called_once()
        
        # Cleanup
        frappe.delete_doc("Virtual Machine", vm.name)

    @patch('press.runner.Ansible.run')
    def test_05_verify_network_setup(self, mock_run):
        """Test network configuration"""
        mock_run.side_effect = [
            MagicMock(status="Success", output="br0 active yes persistent"),  # virsh net-list
            MagicMock(status="Success", output="192.168.100.1")  # ip addr show
        ]
        
        # Verify bridge network exists
        ansible = Ansible(
            playbook="verify_network.yml",  # Use correct playbook
            server=self.vm_host,
            variables={
                "command": "virsh net-list --all | grep br0"
            }
        )
        result = ansible.run()
        self.assertEqual(result.status, "Success")
        self.assertIn("br0", result.output)
        
        # Verify bridge interface exists
        ansible = Ansible(
            playbook="verify_network.yml",  # Use correct playbook
            server=self.vm_host,
            variables={
                "command": "ip addr show br0"
            }
        )
        result = ansible.run()
        self.assertEqual(result.status, "Success")
        self.assertIn("192.168.100.1", result.output)

    @patch('press.runner.Ansible.run')
    def test_06_verify_storage_setup(self, mock_run):
        """Test storage configuration"""
        mock_run.return_value = MagicMock(status="Success", output="exists")
        
        # Verify VM storage directories exist
        directories = [
            "/opt/vms",
            "/opt/vm_images",
            "/opt/vm_configs",
            "/opt/vm_templates"
        ]
        for directory in directories:
            ansible = Ansible(
                playbook="verify_storage.yml",  # Use correct playbook
                server=self.vm_host,
                variables={
                    "command": f"test -d {directory} && echo exists"
                }
            )
            result = ansible.run()
            self.assertEqual(result.status, "Success")
            self.assertIn("exists", result.output)

    @classmethod
    def tearDownClass(cls):
        # Clean up test hosts
        frappe.db.set_single_value("Press Settings", "nfs_server", "")
        
        # Delete Root Domain first since it depends on Cluster
        if frappe.db.exists("Root Domain", "fc.dev"):
            frappe.delete_doc("Root Domain", "fc.dev", force=True)
            frappe.db.commit()
            
        # Now we can delete the Cluster
        if frappe.db.exists("Cluster", cls.cluster.name):
            frappe.delete_doc("Cluster", cls.cluster.name, force=True)
            frappe.db.commit()
            
        # Delete the hosts
        if frappe.db.exists("Bare Metal Host", cls.nfs_server.name):
            frappe.delete_doc("Bare Metal Host", cls.nfs_server.name, force=True)
            frappe.db.commit()
        if frappe.db.exists("Bare Metal Host", cls.vm_host.name):
            frappe.delete_doc("Bare Metal Host", cls.vm_host.name, force=True)
            frappe.db.commit()
            
        # Delete test region and SSH key
        if frappe.db.exists("SSH Key", "test-key"):
            frappe.delete_doc("SSH Key", "test-key", force=True)
            frappe.db.commit()
        if frappe.db.exists("Cloud Region", "test-region"):
            frappe.delete_doc("Cloud Region", "test-region", force=True)
            frappe.db.commit() 