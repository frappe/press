import frappe
import os
import random
import string

def random_string(length=10):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

def setup_demo_environment():
    frappe.flags.in_import = True
    
    # Create Press Settings record if it doesn't exist
    if not frappe.db.get_single_value("Press Settings", "nfs_server"):
        print("Setting up Press Settings...")
        settings = frappe.get_doc("Press Settings")
        settings.nfs_server = "192.168.1.10"  # This will be our NFS server IP
        settings.save()
    
    # Create test SSH key if it doesn't exist
    if not frappe.db.exists("SSH Key", "demo-key"):
        print("Creating demo SSH key...")
        ssh_key = frappe.get_doc({
            "doctype": "SSH Key",
            "title": "Demo SSH Key",
            "public_key": "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCxO4hgPB78KXGDmL7PJl8LGdT/X9CIh5QG+goUL55fOlbVCklE2VhM8qPQyj2D54n5Dp1HYv58Htuze8BtA4yj9vQMFmKX5Ky/ycUIgQIvP9bzjmLiOc6fs0MjaiDGRN8QUjfyq+e+1Bh8QQh06Oyb/AYlEWJxQjsyqr/pX4HakNv0MDrTJYO4DP8F9qh6N20BON7BfmXZHs5xm69wqS0BeNktwJilQ9rOlF3Zj/mBbLCs+RBO6CaHcGCYiUju7pL21LGQJRJGrM2LbzXLI+WgMKLfeTQbvfbgFIxGpGDU8SEDNPfbjsGh8rR7Tbg7KJZ+7oIHnFJXwQgdQW0z5v+p demo@example.com",
            "encrypt_private_key": 0,
            "private_key": "-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQEAsTuIYDwe/Clxg5i+zyZfCxnU/1/QiIeUBvoKFC+eXzpW1QpJ\nRNlYTPKj0Mo9g+eJ+Q6dR2L+fB7bs3vAbQOMo/b0DBZil+Usv8nFCIECLz/W845i\n4jnOn7NDI2ogxkTfEFI38qvnvtQYfEEIdOjsm/wGJRFicUI7Mqq/6V+B2pDb9DA6\n0yWDuAz/BfaoejdtATjewX5l2R7OcZuvcKktAXjZLcCYpUPazpRd2Y/5gWywrPkQ\nTugmh3BgmIlI7u6S9tSxkCUSRqzNi281yyPloDCi33k0G7324BSMRqRg1PEhAzT3\n247BofK0e024OyiWfu6CB5xSV8EIHUFNM+b/qQIDAQABAoIBAQCL36mKLyUR7Cc3\nlI1Uupq3w+pXGI/j7Vy8hR5Eh7NBjH5OD9+Xn5X8tqF7r8fLR5VYF8WuFCTKg9+z\nqRWfbXjDvAK+DAZTfcHLxTlOEgTLv3Q1g1ZPMYqgdnHC0FpOIewtwB0lw3m9YX/B\nRgBCJRNQ07RdOTIpLIERt5OjBohEpHHZ4tR2jDUlnZVVX51VxCx7kzUhtjVXTnAo\nQxYYnKQCi0dXqQoHDUtk+S0TUNVpP9QkqW/SIJhHnpz0/9/+zVyyfBOjHxI99CK1\nbCZaDXnJLYcshyLXzMX/SU1Y+5Cq+ULRY9I4QjJXP+9A8Cd7Iq1R0nJJLfyZ9/sD\nS4AO4YIBAoGBAOHqRhc8Db5D4dHIKosjJP2jtx1N1EWV9qV9w47EAMs/n7vOCbZG\neCG+yMzLGD0nGzPOPm1P7Qm3JeAK9VoMU3v24CJtTqWAPqGNVwLdkHC3wBm56JTU\nrjV+eUGQY0vpI6NVmJJULs4rFd+Gn17M9TpnzXTq+8c9k3p9QxDn4F0pAoGBAMjp\nz6p0XSrjrO8aPSHQ3xXl3YDxKEWxzfUy5lJrZpLvwk1pOnrfQz3L3qqvSwfCbx2I\nAAPKqaFE56qFqoGhnbdTaHQl14XNyC5h0UWj0HuK+GbKlRRWFCSXt6D8h1jGSLrd\nwyYCXEQX2UQE02MiVFGJDGwU+xqm/hADNLK9J4PBAoGBAKZFQBqsLbxcWbVALcAF\nLbOofXsoBvL8J4afMQHWJKxFrLEZ6OhwmudHhSjUr7HLO8/JTMsIDYXx9mW4Gf9D\nLJO7/5E9JaahRMdY4DWuLK75SGvDGDZwYEK26VPoc/Kr9RGm1aPz+2Zs5fFzwHPJ\nAVEdO+8NhtXEVnIMwdFH+qKpAoGAGB4z+Thi+hTY/E8kaUbptTz6vZHNIDuGqoD/\nIPj9S0P8tHDNEWEdjDdT2MKVzO5CwRA5MqnUNR3Q9+vbTvkz6cc6PCcz/HJ5Exlm\nyZ6f94pRN+Dkvv7WmweLBpjuOXeXlWA4Wd8Lh8+gfJ7mEP5ievYVdzXvZbl516wy\ncCQ4b4ECgYAvY5gaM+668nadF6ftUOPzQ2+RG91eCC0OUF2j6G8YNbTdN1wr3xP2\n9BwhjK5dVcsXYSLigMuYJK7+1YCeTtP2XsUiF39Q/kxgPccJkxDXsOUGSYEIJqQF\nSJc8gkjCkLsYzj02s9ODIOU9ZMdQVZ2gdbdgOK23YCpVLmNxVE66iA==\n-----END RSA PRIVATE KEY-----",
            "name": "demo-key",
            "used": 0,
            "status": "Active"
        }).insert()
    
    # Create Cloud Region if it doesn't exist
    if not frappe.db.exists("Cloud Region", "demo-region"):
        print("Creating demo cloud region...")
        region = frappe.get_doc({
            "doctype": "Cloud Region",
            "region_name": "demo-region",
            "provider": "Bare Metal Host",
        }).insert()
    
    # Create Bare Metal Hosts
    if not frappe.db.exists("Bare Metal Host", "nfs-server-demo"):
        print("Creating NFS server bare metal host...")
        nfs_server = frappe.get_doc({
            "doctype": "Bare Metal Host",
            "hostname": "nfs-server-demo",
            "title": "Demo NFS Server",
            "ip": "192.168.1.10",
            "private_ip": "10.0.0.10",
            "ssh_user": "root",
            "ssh_port": 22,
            "total_cpu": 8,
            "total_memory": 16384,  # 16GB in MB
            "total_disk": 500,      # 500GB
            "nfs_exports_directory": "/exports/vm_storage",
            "status": "Active",
            "is_server_prepared": 1,
            "is_server_setup": 1
        }).insert()
    
    if not frappe.db.exists("Bare Metal Host", "vm-host-demo"):
        print("Creating VM host bare metal host...")
        vm_host = frappe.get_doc({
            "doctype": "Bare Metal Host",
            "hostname": "vm-host-demo",
            "title": "Demo VM Host",
            "ip": "192.168.1.20",
            "private_ip": "10.0.0.20",
            "ssh_user": "root",
            "ssh_port": 22,
            "total_cpu": 32,
            "total_memory": 65536,  # 64GB in MB
            "total_disk": 1000,     # 1TB
            "nfs_mount_point": "/mnt/vm_storage",
            "status": "Active",
            "is_server_prepared": 1,
            "is_server_setup": 1,
            "is_vm_host": 1
        }).insert()
    
    # Create test domain if needed
    if not frappe.db.exists("Root Domain", "example.com"):
        print("Creating demo domain...")
        domain = frappe.get_doc({
            "doctype": "Root Domain",
            "name": "example.com",
            "domain": "example.com",
            "is_primary": 1,
            "is_active": 1
        }).insert()
    
    # Create a cluster using the VM host
    if not frappe.db.exists("Cluster", "demo-cluster"):
        print("Creating demo cluster...")
        cluster = frappe.get_doc({
            "doctype": "Cluster",
            "name": "demo-cluster",
            "title": "Demo Cluster",
            "cloud_provider": "Bare Metal Host",
            "bare_metal_host": "vm-host-demo",
            "region": "demo-region",
            "ssh_key": "demo-key",
            "status": "Active"
        }).insert()
        
        # Set the default cluster for domain
        domain = frappe.get_doc("Root Domain", "example.com")
        domain.default_cluster = "demo-cluster"
        domain.save()
    
    # Create a server plan if needed
    if not frappe.db.exists("Server Plan", "demo-plan"):
        print("Creating demo server plan...")
        plan = frappe.get_doc({
            "doctype": "Server Plan",
            "name": "demo-plan",
            "title": "Demo Server Plan",
            "price_usd": 10,
            "instance_type": "4x8",  # 4 CPU, 8GB RAM
            "disk": 50,
            "memory": 8192,
            "vcpu": 4,
            "is_public": 1,
            "for_server": 1,
            "for_database_server": 1
        }).insert()
    
    print("Demo environment setup complete!")

if __name__ == "__main__":
    setup_demo_environment() 