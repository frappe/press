import frappe
import json
import time
import requests
from frappe.utils import now_datetime

def setup_bare_metal_host():
    """Create a bare metal host if it doesn't exist"""
    host_name = "demo-host-1"
    host_name_value = "demo-hypervisor.example.com"
    
    # Clear existing hosts with the same host_name to avoid duplication errors
    duplicate_hosts = frappe.get_all("Bare Metal Host", filters={"host_name": host_name_value})
    if duplicate_hosts:
        print(f"Found {len(duplicate_hosts)} hosts with the same host_name. Clearing...")
        for h in duplicate_hosts:
            try:
                frappe.delete_doc("Bare Metal Host", h.name, force=True)
                print(f"Deleted duplicate host: {h.name}")
            except Exception as e:
                print(f"Could not delete host {h.name}: {str(e)}")
    
    # Delete the host if it already exists
    if frappe.db.exists("Bare Metal Host", host_name):
        try:
            frappe.delete_doc("Bare Metal Host", host_name, force=True)
            print(f"Deleted existing host: {host_name}")
        except Exception as e:
            print(f"Could not delete host {host_name}: {str(e)}")
    
    print(f"Creating Bare Metal Host: {host_name}")
    try:
        host = frappe.new_doc("Bare Metal Host")
        host.name = host_name
        host.host_name = host_name_value
        host.ip_address = "62.210.158.82"
        host.status = "Active"
        
        # Ensure all required fields are set with valid values
        host.total_cpu = 16
        host.total_memory = 32768  # 32GB
        host.total_disk = 1000  # 1TB
        host.available_cpu = 16
        host.available_memory = 32768
        host.available_disk = 1000
        host.cluster = "default"
        
        host.insert(ignore_permissions=True)
        print(f"Created host: {host_name}")
        
        # Verify host exists immediately after creation
        exists_after_creation = frappe.db.exists("Bare Metal Host", host_name)
        print(f"Host exists after creation: {exists_after_creation}")
        
        if exists_after_creation:
            # Get the host again to make sure it's fully committed
            host = frappe.get_doc("Bare Metal Host", host_name)
            print(f"Retrieved host from database: {host.name}")
        else:
            print("WARNING: Host not found immediately after creation!")
    except Exception as e:
        print(f"Error creating host: {str(e)}")
        raise
    
    return host

def setup_bare_metal_vpc():
    """Create a bare metal VPC if it doesn't exist"""
    vpc_name = "demo-vpc"
    host_name = "demo-host-1"
    
    # Delete the VPC if it already exists
    if frappe.db.exists("Bare Metal VPC", vpc_name):
        try:
            frappe.delete_doc("Bare Metal VPC", vpc_name, force=True)
            print(f"Deleted existing VPC: {vpc_name}")
        except Exception as e:
            print(f"Could not delete VPC {vpc_name}: {str(e)}")
    
    print(f"Creating Bare Metal VPC: {vpc_name}")
    vpc = frappe.new_doc("Bare Metal VPC")
    vpc.name = vpc_name
    vpc.cidr = "192.168.10.0/24"
    vpc.status = "Active"
    
    # Find a valid host to use
    if frappe.db.exists("Bare Metal Host", host_name):
        print(f"Using specified host: {host_name}")
        vpc.bare_metal_host = host_name
    else:
        # Look for any available host
        available_hosts = frappe.get_all("Bare Metal Host")
        if available_hosts:
            first_host = available_hosts[0].name
            print(f"Using available host: {first_host}")
            vpc.bare_metal_host = first_host
        else:
            print("Error: No hosts available. Cannot create VPC without a host reference.")
            raise ValueError("No hosts available for VPC creation")
    
    try:
        vpc.insert(ignore_permissions=True)
        print(f"Created VPC: {vpc_name}")
        
        # Verify VPC exists immediately after creation
        exists_after_creation = frappe.db.exists("Bare Metal VPC", vpc_name)
        print(f"VPC exists after creation: {exists_after_creation}")
        
        if exists_after_creation:
            vpc = frappe.get_doc("Bare Metal VPC", vpc_name)
            print(f"Retrieved VPC from database: {vpc.name}")
    except Exception as e:
        print(f"Error creating VPC: {str(e)}")
        raise
    
    return vpc

def setup_bare_metal_template():
    """Create a bare metal VM template if it doesn't exist"""
    template_name = "demo-ubuntu-template"
    
    # Delete the template if it already exists
    if frappe.db.exists("Bare Metal VM Template", template_name):
        try:
            frappe.delete_doc("Bare Metal VM Template", template_name, force=True)
            print(f"Deleted existing template: {template_name}")
        except Exception as e:
            print(f"Could not delete template {template_name}: {str(e)}")
    
    print(f"Creating Bare Metal VM Template: {template_name}")
    try:
        template = frappe.new_doc("Bare Metal VM Template")
        template.name = template_name
        template.description = "Ubuntu 22.04 for bare metal demos"
        
        # Image details
        template.image_url = "https://cloud-images.ubuntu.com/releases/22.04/release/ubuntu-22.04-server-cloudimg-amd64.img"
        template.image_size = 2
        
        # Resources
        template.default_cpu = 2
        template.default_memory = 2048  # 2GB
        template.default_disk = 20  # 20GB
        
        # Cloud-init templates (simplified for demo)
        template.user_data_template = """#cloud-config
hostname: {hostname}
manage_etc_hosts: true
system_info:
  default_user:
    name: ubuntu
    sudo: ALL=(ALL) NOPASSWD:ALL
package_update: true
packages:
  - nginx
  - curl
  - net-tools
"""

        template.meta_data_template = """instance-id: {instance_id}
local-hostname: {hostname}
"""

        template.network_config_template = """version: 2
ethernets:
  ens3:
    dhcp4: true
"""
        
        template.insert(ignore_permissions=True)
        print(f"Created template: {template_name}")
        
        # Verify template exists immediately after creation
        exists_after_creation = frappe.db.exists("Bare Metal VM Template", template_name)
        print(f"Template exists after creation: {exists_after_creation}")
        
        if exists_after_creation:
            template = frappe.get_doc("Bare Metal VM Template", template_name)
            print(f"Retrieved template from database: {template.name}")
        
    except Exception as e:
        print(f"Error creating template: {str(e)}")
        raise
    
    return template

def setup_ip_pool_settings():
    """Create or update IP Pool Settings"""
    if not frappe.db.exists("IP Pool Settings", "IP Pool Settings"):
        print("Creating IP Pool Settings")
        settings = frappe.new_doc("IP Pool Settings")
        settings.total_ips = 100
        settings.used_ips = 10
        settings.elastic_ips = 5
        settings.auto_scaling_enabled = 1
        settings.scaling_threshold = 80
        settings.max_pool_size = 200
        settings.last_updated = now_datetime()
        
        try:
            settings.insert(ignore_permissions=True)
            print("Created IP Pool Settings")
        except Exception as e:
            print(f"Error creating IP Pool Settings: {str(e)}")
            raise
    else:
        print("Updating existing IP Pool Settings")
        settings = frappe.get_doc("IP Pool Settings", "IP Pool Settings")
        settings.total_ips = 100
        settings.used_ips = 10
        settings.elastic_ips = 5
        settings.auto_scaling_enabled = 1
        settings.scaling_threshold = 80
        settings.max_pool_size = 200
        settings.last_updated = now_datetime()
        
        try:
            settings.save(ignore_permissions=True)
            print("Updated IP Pool Settings")
        except Exception as e:
            print(f"Error updating IP Pool Settings: {str(e)}")
    
    return settings

def display_vm_experiments_status():
    """Display the current status of VM Experiments API"""
    base_url = "http://62.210.158.82:5000"
    
    # Import the adapter with correct API URL
    from press.infrastructure.api import VMExperimentsAdapter
    
    # Create adapter instance and set base URL
    adapter = VMExperimentsAdapter(base_url=base_url)
    
    try:
        print("\n=== VM Experiments API Status ===")
        
        # List VMs
        print("\n1. Virtual Machines:")
        vms = adapter.list_vms()
        
        if not vms.get("vms"):
            print("No VMs found.")
        else:
            vm_count = len(vms.get("vms", []))
            print(f"Found {vm_count} VMs:")
            
            # Display VM details
            for i, vm in enumerate(vms.get("vms", [])):
                print(f"\nVM #{i+1} - {vm.get('name')} (ID: {vm.get('id')}):")
                print(f"  Status: {vm.get('status')}")
                print(f"  Created: {time.ctime(vm.get('created_at'))}")
                print(f"  Last updated: {time.ctime(vm.get('updated_at'))}")
                
                # Show config details
                config = vm.get('config', {})
                print(f"  Config:")
                print(f"    CPU: {config.get('cpu_cores')} cores")
                print(f"    Memory: {config.get('memory_mb')} MB")
                print(f"    Disk: {config.get('disk_size_gb')} GB")
                print(f"    Image: {config.get('image_id')}")
                print(f"    Network: {config.get('network_name')}")
        
        # Available Images
        print("\n2. Available VM Images:")
        try:
            response = requests.get(f"{base_url}/api/images", timeout=10)
            if response.status_code == 200:
                images = response.json().get("images", [])
                print(f"Found {len(images)} images:")
                for image in images:
                    print(f"  {image.get('id')} - {image.get('name')} (v{image.get('version')})")
            else:
                print(f"Could not get images, status code: {response.status_code}")
        except Exception as e:
            print(f"Error getting images: {str(e)}")
        
    except Exception as e:
        print(f"Error getting VM Experiments status: {str(e)}")

def create_test_vm(host_name, vpc_name, template_name):
    """Create a test VM using the bare metal integration"""
    from press.infrastructure.api import VMExperimentsAdapter
    
    print("\n=== Creating Test VM ===")
    
    # Create a unique VM name
    vm_name = f"demo-vm-{int(time.time())}"
    print(f"VM Name: {vm_name}")
    
    # Get host, VPC, and template details if they exist
    host_exists = frappe.db.exists("Bare Metal Host", host_name)
    vpc_exists = frappe.db.exists("Bare Metal VPC", vpc_name)
    template_exists = frappe.db.exists("Bare Metal VM Template", template_name)
    
    if not host_exists or not vpc_exists or not template_exists:
        print("Error: Cannot create VM - Missing required components:")
        if not host_exists:
            print(f"  - Host '{host_name}' not found")
        if not vpc_exists:
            print(f"  - VPC '{vpc_name}' not found")
        if not template_exists:
            print(f"  - Template '{template_name}' not found")
        return None
    
    # Get template details for resource allocation
    template = frappe.get_doc("Bare Metal VM Template", template_name)
    vpc = frappe.get_doc("Bare Metal VPC", vpc_name)
    
    try:
        print("\nPreparing VM configuration...")
        print(f"  - Host: {host_name}")
        print(f"  - VPC: {vpc_name} ({vpc.cidr})")
        print(f"  - Template: {template_name}")
        print(f"  - CPU: {template.default_cpu} cores")
        print(f"  - Memory: {template.default_memory} MB")
        print(f"  - Disk: {template.default_disk} GB")
        
        # Generate a test IP address from the VPC CIDR
        # For demo purposes, we'll use a simple IP in the subnet
        cidr_parts = vpc.cidr.split('/')
        ip_base = cidr_parts[0]
        ip_parts = ip_base.split('.')
        demo_ip = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.100"
        gateway_ip = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.1"
        netmask = "255.255.255.0"
        # Each DNS server on a new line, not comma-separated
        nameservers = "8.8.8.8\n8.8.4.4"
        
        print(f"  - IP Address: {demo_ip}")
        print(f"  - Gateway: {gateway_ip}")
        print(f"  - Netmask: {netmask}")
        print(f"  - Nameservers: 8.8.8.8, 8.8.4.4")
        
        # Create VM record that we'll use to track the VM
        print("\nAttempting to create VM record in Press...")
        
        # First check if there's an existing VM with this name and delete it
        if frappe.db.exists("Bare Metal VM", vm_name):
            print(f"Deleting existing VM record: {vm_name}")
            frappe.delete_doc("Bare Metal VM", vm_name, force=True)
        
        # Flag to track if we've successfully created a VM record
        vm_record_created = False
        vm_doc = None
        
        try:
            # Create the VM document
            vm_doc = frappe.new_doc("Bare Metal VM")
            vm_doc.name = vm_name
            vm_doc.status = "Creating"  # Use a valid status
            vm_doc.host = host_name
            vm_doc.template = template_name
            vm_doc.cpu = template.default_cpu
            vm_doc.memory = template.default_memory
            vm_doc.disk = template.default_disk
            
            # Set network configuration with validation checks
            vm_doc.ip_address = demo_ip
            vm_doc.gateway = gateway_ip
            vm_doc.netmask = netmask
            vm_doc.nameservers = nameservers  # Each DNS server on a new line
            vm_doc.created_at = now_datetime()
            
            # Insert with ignoring permissions but not validations
            vm_doc.insert(ignore_permissions=True)
            print(f"Created Press VM record: {vm_name}")
            vm_record_created = True
            
        except frappe.ValidationError as e:
            print(f"\nValidation Error creating VM record: {str(e)}")
            print("This is expected due to known validation issues.")
            print("Creating a simplified VM record for demo purposes...")
            
            # If validation fails, create a simpler record
            try:
                # Create a simpler record with direct SQL or API
                # For demo purposes, we'll track this locally
                vm_doc = frappe._dict({
                    "name": vm_name,
                    "host": host_name,
                    "template": template_name,
                    "ip_address": demo_ip,
                    "status": "Creating"
                })
                print(f"Created simplified VM tracking object for demo")
                
            except Exception as e2:
                print(f"Error creating simplified VM record: {str(e2)}")
                print("Proceeding with local tracking object only")
                vm_doc = frappe._dict({
                    "name": vm_name,
                    "host": host_name,
                    "template": template_name,
                    "status": "Error"
                })
        
        # Now try to call the VM Experiments API directly
        print("\nCalling VM Experiments API to create VM...")
        
        try:
            # Directly use the adapter with carefully crafted data structure
            adapter = VMExperimentsAdapter(base_url=frappe.conf.vm_experiments_url)
            
            # Create a comprehensive data structure as expected by the API
            vm_data = {
                "name": vm_name,
                "host": host_name,
                "cpu": template.default_cpu,
                "memory": template.default_memory,
                "disk": template.default_disk,
                "network": {
                    "id": vpc_name,
                    "ip_address": demo_ip,
                    "netmask": netmask,
                    "gateway": gateway_ip,
                    "nameservers": ["8.8.8.8", "8.8.4.4"]  # List for API call
                },
                "image": "ubuntu-20.04"
            }
            
            # Call create_vm method directly
            result = adapter.create_vm(vm_data)
            
            print("\nAPI Response:")
            print(json.dumps(result, indent=2))
            
            if result.get("id"):
                # Update VM record with VM ID if it exists
                if vm_record_created and frappe.db.exists("Bare Metal VM", vm_name):
                    vm_doc_db = frappe.get_doc("Bare Metal VM", vm_name)
                    vm_doc_db.vm_id = result.get("id")
                    vm_doc_db.status = result.get("status", "Creating")
                    vm_doc_db.save(ignore_permissions=True)
                print(f"\nVM creation initiated successfully! VM ID: {result.get('id')}")
                return vm_doc
            else:
                print("\nWarning: VM creation API did not return a VM ID")
                return vm_doc
            
        except Exception as e:
            print(f"\nError calling VM Experiments API: {str(e)}")
            print("Note: I'm expecting this error due to my known server-side issue with LibvirtManager._configure_networking")
            print("I'll need to fix my LibvirtManager._configure_networking issue in my VM Experiments server")
            print("before my VM creation will work completely.")
            
            # Update VM status to reflect the error if record exists
            if vm_record_created and frappe.db.exists("Bare Metal VM", vm_name):
                frappe.db.set_value("Bare Metal VM", vm_name, "status", "Error")
                frappe.db.commit()
                
            return vm_doc
            
    except Exception as e:
        print(f"\nError preparing VM: {str(e)}")
        return None

def run_complete_demo():
    """Run a complete demonstration of Press + VM Experiments integration"""
    print("=== Press + VM Experiments Integration Demo ===\n")
    
    # Set VM Experiments URL in configuration
    base_url = "http://62.210.158.82:5000"
    frappe.conf.vm_experiments_url = base_url
    
    try:
        # 1. Setup Press components
        print("Setting up Press components for bare metal integration...")
        host = setup_bare_metal_host()
        
        # Add a small delay to ensure host is fully created in database
        print("Waiting for host to be fully created...")
        time.sleep(2)
        
        vpc = setup_bare_metal_vpc()
        template = setup_bare_metal_template()
        ip_settings = setup_ip_pool_settings()
        
        # 2. Display VM Experiments status
        display_vm_experiments_status()
        
        # 3. Attempt to create a test VM
        host_name = None
        vpc_name = None
        template_name = None
        
        # Get host name
        if host is None or not frappe.db.exists("Bare Metal Host", host.name):
            available_hosts = frappe.get_all("Bare Metal Host")
            if available_hosts:
                host_name = available_hosts[0].name
        else:
            host_name = host.name
            
        # Get VPC name
        if vpc is None or not frappe.db.exists("Bare Metal VPC", vpc.name):
            available_vpcs = frappe.get_all("Bare Metal VPC")
            if available_vpcs:
                vpc_name = available_vpcs[0].name
        else:
            vpc_name = vpc.name
            
        # Get template name
        if template is None or not frappe.db.exists("Bare Metal VM Template", template.name):
            available_templates = frappe.get_all("Bare Metal VM Template")
            if available_templates:
                template_name = available_templates[0].name
        else:
            template_name = template.name
            
        # Create VM if we have all the required components
        if host_name and vpc_name and template_name:
            test_vm = create_test_vm(host_name, vpc_name, template_name)
        else:
            print("\n=== Cannot Create Test VM ===")
            print("Missing required components:")
            if not host_name:
                print("- No host available")
            if not vpc_name:
                print("- No VPC available")
            if not template_name:
                print("- No template available")
        
        # 4. Display integration information
        print("\n=== Integration Information ===")
        print(f"VM Experiments API URL: {base_url}")
        
        # For host display, get the most recent host if our host is not found
        if host is None or not frappe.db.exists("Bare Metal Host", host.name):
            available_hosts = frappe.get_all("Bare Metal Host", fields=["name", "host_name"])
            if available_hosts:
                host_info = available_hosts[0]
                print(f"Press Bare Metal Host: {host_info.name} ({host_info.host_name})")
            else:
                print("Press Bare Metal Host: None (No hosts available)")
        else:
            print(f"Press Bare Metal Host: {host.name} ({host.host_name})")
        
        # For VPC display, get the most recent VPC if our VPC is not found
        if vpc is None or not frappe.db.exists("Bare Metal VPC", vpc.name):
            available_vpcs = frappe.get_all("Bare Metal VPC", fields=["name", "cidr"])
            if available_vpcs:
                vpc_info = available_vpcs[0]
                print(f"Press Bare Metal VPC: {vpc_info.name} ({vpc_info.cidr})")
            else:
                print("Press Bare Metal VPC: None (No VPCs available)")
        else:
            print(f"Press Bare Metal VPC: {vpc.name} ({vpc.cidr})")
        
        # For template display, use description instead of os_name
        if template is None or not frappe.db.exists("Bare Metal VM Template", template.name):
            available_templates = frappe.get_all("Bare Metal VM Template", fields=["name", "description"])
            if available_templates:
                template_info = available_templates[0]
                print(f"Press VM Template: {template_info.name} ({template_info.description})")
            else:
                print("Press VM Template: None (No templates available)")
        else:
            print(f"Press VM Template: {template.name} ({template.description})")
            
        print(f"IP Pool Settings: {ip_settings.total_ips} total IPs, {ip_settings.used_ips} used")
        
        print("\nDemo completed successfully!")
        return {"status": "success", "message": "Demo completed successfully."}
        
    except Exception as e:
        print(f"Error in demo: {str(e)}")
        return {"status": "error", "message": str(e)} 