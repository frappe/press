import unittest
import frappe
from unittest.mock import MagicMock, patch
from frappe.test_runner import make_test_records

class TestNFSOptimization(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create test data
        cls.create_test_data()
        
    @classmethod
    def create_test_data(cls):
        # Create test NFS server
        if not frappe.db.exists("Bare Metal Host", "test-nfs-server"):
            frappe.get_doc({
                "doctype": "Bare Metal Host",
                "hostname": "test-nfs-server",
                "title": "Test NFS Server",
                "ip": "192.168.1.10",
                "private_ip": "10.0.0.10",
                "ssh_user": "root",
                "ssh_port": 22,
                "total_cpu": 8,
                "total_memory": 16384,  # 16GB in MB
                "total_disk": 500,      # 500GB
                "available_disk": 300,  # 300GB available
                "nfs_exports_directory": "/exports/vm_storage",
                "status": "Active",
                "is_server_prepared": 1,
                "is_server_setup": 1,
                "is_nfs_server": 1
            }).insert(ignore_permissions=True)
        
        # Create test NFS client
        if not frappe.db.exists("Bare Metal Host", "test-nfs-client"):
            frappe.get_doc({
                "doctype": "Bare Metal Host",
                "hostname": "test-nfs-client",
                "title": "Test NFS Client",
                "ip": "192.168.1.20",
                "private_ip": "10.0.0.20",
                "ssh_user": "root",
                "ssh_port": 22,
                "total_cpu": 16,
                "total_memory": 32768,  # 32GB in MB
                "total_disk": 500,      # 500GB
                "nfs_mount_point": "/mnt/vm_storage",
                "status": "Active",
                "is_server_prepared": 1,
                "is_server_setup": 1
            }).insert(ignore_permissions=True)
        
    @classmethod
    def tearDownClass(cls):
        # Clean up test data
        if frappe.db.exists("Bare Metal Host", "test-nfs-server"):
            frappe.db.delete("Bare Metal Host", "test-nfs-server")
        
        if frappe.db.exists("Bare Metal Host", "test-nfs-client"):
            frappe.db.delete("Bare Metal Host", "test-nfs-client")
            
    @patch('press.runner.Ansible.run')
    def test_nfs_server_optimization(self, mock_run):
        """Test NFS server optimization"""
        # Create a mock return value
        mock_return = MagicMock()
        mock_return.status = "Success"
        mock_run.return_value = mock_return
        
        # Get test server
        nfs_server = frappe.get_doc("Bare Metal Host", "test-nfs-server")
        
        # Call optimization
        nfs_server.optimize_nfs_server()
        frappe.db.commit()
        
        # Verify mock was called with correct args
        mock_run.assert_called_once()
        args = mock_run.call_args[0]
        kwargs = mock_run.call_args[1]
        
        # Validate playbook and variables
        self.assertEqual(kwargs.get('playbook'), 'nfs_server_optimize.yml')
        self.assertEqual(kwargs.get('variables').get('nfs_exports_directory'), nfs_server.nfs_exports_directory)
        self.assertEqual(kwargs.get('variables').get('nfs_rsize'), 1048576)
        self.assertEqual(kwargs.get('variables').get('nfs_wsize'), 1048576)
        
    @patch('press.runner.Ansible.run')
    def test_nfs_connectivity_check(self, mock_run):
        """Test NFS connectivity check"""
        # Create a mock return value
        mock_return = MagicMock()
        mock_return.status = "Success"
        mock_run.return_value = mock_return
        
        # Get test client
        nfs_client = frappe.get_doc("Bare Metal Host", "test-nfs-client")
        
        # Set NFS server in settings
        frappe.db.set_single_value("Press Settings", "nfs_server", "192.168.1.10")
        
        # Call connectivity check
        result = nfs_client.check_nfs_connectivity()
        
        # Verify mock was called with correct args
        mock_run.assert_called_once()
        kwargs = mock_run.call_args[1]
        
        # Validate playbook and variables
        self.assertEqual(kwargs.get('playbook'), 'nfs_connectivity_check.yml')
        self.assertEqual(kwargs.get('variables').get('nfs_server_ip'), "192.168.1.10")
        self.assertTrue(result)
    
    @patch('press.utils.get_nfs_server')
    def test_get_nfs_server(self, mock_get_nfs_server):
        """Test get_nfs_server function with load balancing"""
        # First test getting from settings
        frappe.db.set_single_value("Press Settings", "nfs_server", "192.168.1.50")
        from press.utils import get_nfs_server
        
        # Call the function directly to test
        server_ip = get_nfs_server()
        self.assertEqual(server_ip, "192.168.1.50")
        
        # Now test finding server with most available disk
        frappe.db.set_single_value("Press Settings", "nfs_server", "")
        
        # Create another test server with more available disk
        if not frappe.db.exists("Bare Metal Host", "test-nfs-server2"):
            frappe.get_doc({
                "doctype": "Bare Metal Host",
                "hostname": "test-nfs-server2",
                "title": "Test NFS Server 2",
                "ip": "192.168.1.11",
                "ssh_user": "root",
                "ssh_port": 22,
                "total_cpu": 8,
                "total_memory": 16384,
                "total_disk": 500,
                "available_disk": 400,  # This one has more available disk
                "nfs_exports_directory": "/exports/vm_storage",
                "status": "Active",
                "is_server_prepared": 1,
                "is_server_setup": 1,
                "is_nfs_server": 1
            }).insert(ignore_permissions=True)
        
        # Call the function again to test load balancing
        server_ip = get_nfs_server()
        
        # It should select the server with more available disk
        self.assertEqual(server_ip, "192.168.1.11")
        
        # Clean up
        if frappe.db.exists("Bare Metal Host", "test-nfs-server2"):
            frappe.db.delete("Bare Metal Host", "test-nfs-server2")

if __name__ == '__main__':
    unittest.main() 