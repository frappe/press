# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe.model.document import Document
from press.press.doctype.server.server import BaseServer
from press.runner import Ansible
from frappe.utils import get_url
import re
import requests
from press.utils import log_error
from press.utils.client import Client


@frappe.whitelist()
def provision_host(docname):
    """Module-level function for provisioning a bare metal host"""
    doc = frappe.get_doc("Bare Metal Host", docname)
    return doc._provision_host()


@frappe.whitelist()
def prepare_host(docname):
    """Module-level function for preparing a bare metal host"""
    doc = frappe.get_doc("Bare Metal Host", docname)
    return doc._prepare_host()


@frappe.whitelist()
def setup_vm_host(docname):
    """Module-level function for setting up a bare metal host as VM host"""
    doc = frappe.get_doc("Bare Metal Host", docname)
    return doc._setup_vm_host()


class BareMetalHost(BaseServer):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        from press.press.doctype.resource_tag.resource_tag import ResourceTag
        from press.press.doctype.server_mount.server_mount import ServerMount

        agent_password: DF.Password | None
        cluster: DF.Link | None
        domain: DF.Link | None
        frappe_public_key: DF.Code | None
        frappe_user_password: DF.Password | None
        hostname: DF.Data
        hostname_abbreviation: DF.Data | None
        ip: DF.Data | None
        mounts: DF.Table[ServerMount]
        private_ip: DF.Data | None
        public: DF.Check
        ssh_port: DF.Int
        ssh_user: DF.Data | None
        status: DF.Literal["Pending", "Installing", "Active", "Broken", "Archived"]
        tags: DF.Table[ResourceTag]
        team: DF.Link | None
        title: DF.Data | None
        total_cpu: DF.Int
        total_memory: DF.Int
        total_disk: DF.Int
        available_cpu: DF.Int
        available_memory: DF.Int
        available_disk: DF.Int
    # end: auto-generated types

    # Add a property for virtual_machine to avoid AttributeError
    @property
    def virtual_machine(self):
        return None

    def validate(self):
        # Only validate resources if they are already set
        if self.status == "Active":
            self.validate_resources()
        elif self.status == "Pending" or not self.status:
            # For new hosts, we only need minimal validation
            self._validate_minimal_fields()

    def _validate_minimal_fields(self):
        """Ensure the minimal required fields for provisioning are set"""
        if not self.hostname:
            frappe.throw("Hostname is required")
        if not self.ip:
            frappe.throw("IP is required")
        if not self.ssh_user:
            frappe.throw("SSH User is required")
        if not self.ssh_port:
            frappe.throw("SSH Port is required")

    def validate_resources(self):
        """Validate resource configurations"""
        # Initialize resources if not already set
        self.initialize_resources()
        
        # Validate total resources
        if not self.total_cpu or self.total_cpu <= 0:
            frappe.throw("Total CPU must be greater than 0")
        if not self.total_memory or self.total_memory <= 0:
            frappe.throw("Total Memory must be greater than 0")
        if not self.total_disk or self.total_disk <= 0:
            frappe.throw("Total Disk must be greater than 0")

        # Validate available resources don't exceed total
        if self.available_cpu > self.total_cpu:
            frappe.throw("Available CPU cannot be more than total CPU")
        if self.available_memory > self.total_memory:
            frappe.throw("Available memory cannot be more than total memory")
        if self.available_disk > self.total_disk:
            frappe.throw("Available disk cannot be more than total disk")

        # Ensure non-negative values
        if self.available_cpu < 0:
            self.available_cpu = 0
        if self.available_memory < 0:
            self.available_memory = 0
        if self.available_disk < 0:
            self.available_disk = 0

    def initialize_resources(self):
        """Initialize resource values if not set"""
        # Convert all resource fields to integers to avoid comparison issues
        self.total_cpu = int(self.total_cpu or 0)
        self.total_memory = int(self.total_memory or 0)
        self.total_disk = int(self.total_disk or 0)
        
        # Set available resources if not already set
        if not self.available_cpu:
            self.available_cpu = self.total_cpu
        else:
            self.available_cpu = int(self.available_cpu)
            
        if not self.available_memory:
            self.available_memory = self.total_memory
        else:
            self.available_memory = int(self.available_memory)
            
        if not self.available_disk:
            self.available_disk = self.total_disk
        else:
            self.available_disk = int(self.available_disk)

    def autoname(self):
        """Override to prevent domain appending for bare metal hosts"""
        self.name = self.hostname

    def after_insert(self):
        """Override to prevent DNS record creation for bare metal hosts"""
        pass

    def fetch_volumes_from_virtual_machine(self):
        """Override to avoid virtual_machine attribute error"""
        pass

    def update_virtual_machine_name(self):
        """Override to avoid virtual_machine attribute error"""
        pass

    def validate_mounts(self):
        """Override to avoid virtual_machine attribute error"""
        # Bare metal hosts don't need to validate mounts the same way as virtual machines
        pass

    @frappe.whitelist()
    def provision_host(self):
        """Provision the bare metal host by setting up agent using Ansible"""
        return self._provision_host()

    def _provision_host(self):
        """Run ansible playbook to provision the host with agent and gather system information"""
        # First, set status to Installing
        self.db_set("status", "Installing")
        
        # Run the vm-host playbook to set up the agent
        ansible = Ansible(
            playbook="vm-host.yml",
            server=self,
            user=self.ssh_user,
            port=self.ssh_port,
            variables={},
        )
        play = ansible.run()
        
        # If the vm-host playbook succeeds, run the gather_facts playbook for detailed system info
        if play.status == "Success":
            try:
                # Run gather_facts playbook for comprehensive system information
                facts_ansible = Ansible(
                    playbook="gather_facts.yml",
                    server=self,
                    user=self.ssh_user,
                    port=self.ssh_port,
                    variables={},
                )
                facts_play = facts_ansible.run()
                
                if facts_play.status == "Success" and hasattr(facts_play, 'play_recap'):
                    # Extract system facts from ansible play_recap
                    if hasattr(facts_play.play_recap, 'ansible_facts'):
                        facts = facts_play.play_recap.ansible_facts
                        
                        # Update CPU info if available
                        if facts.get('ansible_processor_vcpus'):
                            self.db_set("total_cpu", int(facts.get('ansible_processor_vcpus')))
                            self.db_set("available_cpu", int(facts.get('ansible_processor_vcpus')))
                            
                        # Update memory info if available
                        if facts.get('ansible_memtotal_mb'):
                            self.db_set("total_memory", int(facts.get('ansible_memtotal_mb')))
                            self.db_set("available_memory", int(facts.get('ansible_memtotal_mb')))
                            
                        # Update OS info if available
                        if facts.get('ansible_distribution') and facts.get('ansible_distribution_version'):
                            os_info = f"{facts.get('ansible_distribution')} {facts.get('ansible_distribution_version')}"
                            self.db_set("os_info", os_info)
                            
                        # Update IP info if available
                        if facts.get('ansible_default_ipv4') and facts.get('ansible_default_ipv4').get('address'):
                            # Only update private_ip if not already set
                            if not self.private_ip:
                                self.db_set("private_ip", facts.get('ansible_default_ipv4').get('address'))
                                
                        # Check for available disk if ansible_mounts is available
                        if facts.get('ansible_mounts'):
                            # Sum up the available space from all mount points
                            total_available_gb = 0
                            for mount in facts.get('ansible_mounts', []):
                                if mount.get('size_available'):
                                    # Convert bytes to GB
                                    available_gb = mount.get('size_available') / (1024 * 1024 * 1024)
                                    total_available_gb += available_gb
                                    
                            if total_available_gb > 0:
                                self.db_set("available_disk", int(total_available_gb))
                                # If total_disk isn't set yet, calculate from used + available
                                if not self.total_disk:
                                    total_used_gb = 0
                                    for mount in facts.get('ansible_mounts', []):
                                        if mount.get('size_total') and mount.get('size_available'):
                                            used_gb = (mount.get('size_total') - mount.get('size_available')) / (1024 * 1024 * 1024)
                                            total_used_gb += used_gb
                                    
                                    self.db_set("total_disk", int(total_available_gb + total_used_gb))
                        
                        # Check VM capabilities
                        if facts.get('vm_capability') or facts.get('kvm_modules_loaded'):
                            self.db_set("is_vm_host", 1)
                            frappe.msgprint("VM/KVM capability detected. This host can be configured as a VM host.")
                            
                        # Check NFS server capabilities 
                        if facts.get('nfs_server_capability'):
                            frappe.msgprint("NFS server capability detected. This host can be configured as an NFS server.")
                            
                        # If NFS server is already running
                        if facts.get('nfs_server_running'):
                            self.db_set("is_nfs_server", 1)
                            frappe.msgprint("NFS server detected as running on this host.")
                            
                        # Display network interfaces for reference
                        if facts.get('network_interfaces'):
                            interfaces_str = "\n".join(facts.get('network_interfaces', []))
                            frappe.msgprint(f"Network interfaces detected:\n{interfaces_str}")
            except Exception as e:
                frappe.log_error(f"Error gathering advanced system information: {str(e)}", server=self.as_dict())
                # Continue with basic info gathering even if advanced gathering fails
                
        # Retrieve basic system information as a fallback
        self._retrieve_system_info()
        
        # Mark as active
        self.db_set("status", "Active")
        return play
    
    def _retrieve_system_info(self):
        """Retrieve comprehensive system information via SSH and update fields"""
        try:
            client = Client(self.name)
            
            # Get CPU count
            cpu_count = client.execute("nproc --all", _raise=False)
            if cpu_count and cpu_count.stdout:
                self.db_set("total_cpu", int(cpu_count.stdout.strip()))
                # Set available_cpu same as total_cpu initially
                self.db_set("available_cpu", int(cpu_count.stdout.strip()))
                
            # Get memory in MB
            memory_cmd = "free -m | awk '/^Mem:/ {print $2}'"
            memory = client.execute(memory_cmd, _raise=False)
            if memory and memory.stdout:
                total_memory = int(memory.stdout.strip())
                self.db_set("total_memory", total_memory)
                # Set available_memory same as total_memory initially
                self.db_set("available_memory", total_memory)
                
            # Get disk space in GB
            disk_cmd = "df -BG --total | grep total | awk '{print $2}' | sed 's/G//'"
            disk = client.execute(disk_cmd, _raise=False)
            if disk and disk.stdout:
                total_disk = int(float(disk.stdout.strip()))
                self.db_set("total_disk", total_disk)
                # Set available_disk same as total_disk initially
                self.db_set("available_disk", total_disk)
                
            # Get OS information
            os_cmd = "cat /etc/os-release | grep '^PRETTY_NAME' | cut -d'\"' -f2"
            os_info = client.execute(os_cmd, _raise=False)
            if os_info and os_info.stdout:
                frappe.db.set_value("Bare Metal Host", self.name, "os_info", os_info.stdout.strip())
                
            # Get private IP if not already set
            if not self.private_ip:
                private_ip_cmd = "ip -4 addr show | grep -v '127.0.0.1' | grep 'inet ' | awk '{print $2}' | cut -d'/' -f1 | head -n1"
                private_ip = client.execute(private_ip_cmd, _raise=False)
                if private_ip and private_ip.stdout:
                    self.db_set("private_ip", private_ip.stdout.strip())
                    
            # Check if this system can be an NFS server
            nfs_check = client.execute("command -v nfs-kernel-server || command -v nfs-utils", _raise=False)
            if nfs_check and nfs_check.stdout:
                # NFS server capability exists, check for exports directory
                exports_dir = self.nfs_exports_directory or "/exports/vm_storage"
                dir_check = client.execute(f"[ -d {exports_dir} ] && echo 'exists' || echo 'not found'", _raise=False)
                if dir_check and dir_check.stdout and 'exists' in dir_check.stdout:
                    # Directory exists, suggest this can be an NFS server
                    frappe.msgprint(f"NFS exports directory found at {exports_dir}. This host can be configured as an NFS server.")
            
            # Check if this is already an NFS server
            if not self.is_nfs_server:
                nfs_proc = client.execute("ps aux | grep -v grep | grep nfsd", _raise=False)
                if nfs_proc and nfs_proc.stdout and len(nfs_proc.stdout.strip()) > 0:
                    frappe.msgprint("NFS server processes detected. This host appears to be running an NFS server.")
                    
            # Get VM capability
            kvm_check = client.execute("lsmod | grep kvm", _raise=False)
            if kvm_check and kvm_check.stdout and len(kvm_check.stdout.strip()) > 0:
                # Host has KVM capability
                self.db_set("is_vm_host", 1)
                frappe.msgprint("KVM capability detected. This host can be configured as a VM host.")
                
            frappe.db.commit()
            frappe.msgprint("System information retrieved successfully.")
            
        except Exception as e:
            frappe.log_error(f"Error retrieving system information: {str(e)}", server=self.as_dict())
            frappe.msgprint(f"Error retrieving system information: {str(e)}", indicator="red")

    @frappe.whitelist()
    def prepare_server(self):
        """
        Prepare the bare metal host similar to how servers are prepared
        """
        frappe.enqueue_doc(self.doctype, self.name, "_prepare_server", queue="long", timeout=2400)

    def _prepare_server(self):
        try:
            # Create a server-like object with the properties Ansible needs
            class ServerObj:
                def __init__(self, doc):
                    self.name = doc.name
                    self.ip = doc.ip
                    self.doctype = doc.doctype
            
            server_obj = ServerObj(self)
            
            # Default to Generic playbook if provider not specified
            playbook = "generic.yml"
            user = self.ssh_user or "root"
            
            # Select correct playbook based on provider if specified
            if hasattr(self, 'provider'):
                if self.provider == "Scaleway":
                    playbook = "scaleway.yml"
                    user = "ubuntu"
                    variables = {
                        "private_ip": self.private_ip if hasattr(self, 'private_ip') else None,
                        "private_mac_address": self.private_mac_address if hasattr(self, 'private_mac_address') else None,
                        "private_vlan_id": self.private_vlan_id if hasattr(self, 'private_vlan_id') else None,
                    }
                    ansible = Ansible(playbook=playbook, server=server_obj, user=user, variables=variables)
                elif self.provider == "AWS EC2":
                    playbook = "aws.yml"
                    user = "ubuntu"
                    ansible = Ansible(playbook=playbook, server=server_obj, user=user)
                elif self.provider == "OCI":
                    playbook = "oci.yml"
                    user = "ubuntu"
                    ansible = Ansible(playbook=playbook, server=server_obj, user=user)
                else:
                    ansible = Ansible(playbook=playbook, server=server_obj, user=user)
            else:
                ansible = Ansible(playbook=playbook, server=server_obj, user=user)

            play = ansible.run()
            self.reload()
            if play.status == "Success":
                self.is_server_prepared = True
                self.status = "Installing"
                self.save()
            return play
        except Exception:
            log_error("Bare Metal Host Preparation Exception", server=self.as_dict())

    @frappe.whitelist()
    def setup_server(self):
        """
        Setup the server with necessary components
        """
        self.status = "Installing"
        self.save()
        frappe.enqueue_doc(self.doctype, self.name, "_setup_server", queue="long", timeout=2400)

    def _setup_server(self):
        try:
            # Create a server-like object with the properties Ansible needs
            class ServerObj:
                def __init__(self, doc):
                    self.name = doc.name
                    self.ip = doc.ip
                    self.doctype = doc.doctype
            
            server_obj = ServerObj(self)
            
            ansible = Ansible(
                playbook="server.yml",
                server=server_obj,
                user=self.ssh_user or "root",
                port=self.ssh_port or 22,
            )
            play = ansible.run()
            self.reload()
            if play.status == "Success":
                self.is_server_setup = True
                self.status = "Active"
                self.save()
            return play
        except Exception:
            log_error("Bare Metal Host Setup Exception", server=self.as_dict())

    @frappe.whitelist()
    def setup_vm_host(self):
        """
        Set up server for KVM virtualization
        """
        # Validate required fields
        if not self.ip:
            frappe.throw("IP address is required")
        if not self.ssh_user:
            frappe.throw("SSH user is required")
        if not self.ssh_port:
            frappe.throw("SSH port is required")
            
        # Check if server is prepared
        if not self.is_server_prepared:
            frappe.throw("Server must be prepared before setting up as VM host. Please run 'Prepare Server' first.")
            
        # Update status and enqueue setup
        self.status = "Installing"
        self.save()
        frappe.enqueue_doc(self.doctype, self.name, "_setup_vm_host", queue="long", timeout=2400)

    def _setup_vm_host(self):
        """Run ansible playbook to set up KVM virtualization"""
        try:
            # Create a server-like object with the properties Ansible needs
            class ServerObj:
                def __init__(self, doc):
                    self.name = doc.name
                    self.ip = doc.ip
                    self.doctype = doc.doctype
            
            server_obj = ServerObj(self)
            
            # Set up variables for the playbook
            variables = {
                "configure_network": True,
                "configure_storage": True,
                "configure_firewall": True,
                "setup_vm_storage": True,
                "optimize_io": True,
                "storage_path": "/var/lib/libvirt/images",
                "vm_directory": "/opt/vms",
                "vm_images_directory": "/opt/vm_images",
                "vm_config_directory": "/opt/vm_configs",
                "vm_templates_directory": "/opt/vm_templates",
                "bridge_network": {
                    "name": "br0",
                    "ip": "192.168.100.1",
                    "netmask": "255.255.255.0",
                    "dhcp_start": "192.168.100.100",
                    "dhcp_end": "192.168.100.200"
                }
            }
            
            ansible = Ansible(
                playbook="bare_metal_vm_host.yml",
                server=server_obj,
                user=self.ssh_user or "root",
                port=self.ssh_port or 22,
                variables=variables
            )
            
            play = ansible.run()
            self.reload()
            
            if play.status == "Success":
                self.db_set("is_vm_host_setup", 1)
                self.db_set("is_vm_host", 1)  # Mark as VM host
                self.db_set("status", "Active")
                frappe.msgprint("VM host setup completed successfully")
            else:
                self.db_set("status", "Broken")
                frappe.throw(f"VM host setup failed: {play.status}")
                
            return play

        except Exception as e:
            self.db_set("status", "Broken")
            log_error("Bare Metal VM Host Setup Exception", server=self.as_dict(), error=str(e))
            frappe.throw(f"VM host setup failed: {str(e)}")

    @frappe.whitelist()
    def install_nginx(self):
        """
        Install and configure Nginx
        """
        self.status = "Installing"
        self.save()
        frappe.enqueue_doc(self.doctype, self.name, "_install_nginx", queue="long", timeout=1200)

    def _install_nginx(self):
        try:
            # Create a server-like object with the properties Ansible needs
            class ServerObj:
                def __init__(self, doc):
                    self.name = doc.name
                    self.ip = doc.ip
                    self.doctype = doc.doctype
            
            server_obj = ServerObj(self)
            
            ansible = Ansible(
                playbook="nginx.yml",
                server=server_obj,
                user=self.ssh_user or "root",
                port=self.ssh_port or 22,
            )
            ansible.run()
        except Exception:
            log_error("Bare Metal Host Nginx Installation Exception", server=self.as_dict())

    @frappe.whitelist()
    def install_filebeat(self):
        """
        Install and configure Filebeat for logging
        """
        frappe.enqueue_doc(self.doctype, self.name, "_install_filebeat", queue="long", timeout=1200)

    def _install_filebeat(self):
        try:
            # Get log server from configuration if available
            log_server = frappe.db.get_single_value("Press Settings", "log_server")
            logstash = f"{log_server}:5044" if log_server else "logstash:5044"
            
            # Create a server-like object with the properties Ansible needs
            class ServerObj:
                def __init__(self, doc):
                    self.name = doc.name
                    self.ip = doc.ip
                    self.doctype = doc.doctype
            
            server_obj = ServerObj(self)
            
            ansible = Ansible(
                playbook="filebeat.yml",
                server=server_obj,
                user=self.ssh_user or "root",
                port=self.ssh_port or 22,
                variables={"logstash": logstash}
            )
            ansible.run()
        except Exception:
            log_error("Bare Metal Host Filebeat Installation Exception", server=self.as_dict())

    def get_actions(self):
        """Add VM host specific actions"""
        actions = super().get_actions()
        
        # Add provision host action for newly created hosts
        if self.status == "Pending":
            actions.append({
                "action": "Provision Host",
                "description": "Install agent on bare metal host",
                "button_label": "Provision",
                "condition": self.status == "Pending",
                "doc_method": "provision_host",
                "group": "Bare Metal Host Actions",
            })
        
        # Add prepare host action after provision
        if self.status == "Installing":
            actions.append({
                "action": "Prepare Host",
                "description": "Setup server with basic configurations",
                "button_label": "Prepare",
                "condition": self.status == "Installing",
                "doc_method": "prepare_server",
                "group": "Bare Metal Host Actions",
            })
            
        # Add setup VM host actions if not active
        if self.status != "Active":
            actions.extend([
                {
                    "action": "Setup as VM Host",
                    "description": "Configure host for KVM virtualization",
                    "button_label": "Setup VM Host",
                    "condition": True,
                    "doc_method": "setup_vm_host",
                    "group": "Bare Metal Host Actions",
                },
                {
                    "action": "Setup as VM Host with NFS",
                    "description": "Configure host for KVM virtualization with NFS storage",
                    "button_label": "Setup VM Host with NFS",
                    "condition": True,
                    "doc_method": "setup_vm_host_with_nfs",
                    "group": "Bare Metal Host Actions",
                },
                {
                    "action": "Setup as NFS Server",
                    "description": "Configure host as NFS server for VM storage",
                    "button_label": "Setup NFS Server",
                    "condition": True,
                    "doc_method": "setup_nfs_server",
                    "group": "Bare Metal Host Actions",
                },
                {
                    "action": "Setup as NFS Client",
                    "description": "Configure host as NFS client for VM storage",
                    "button_label": "Setup NFS Client",
                    "condition": True,
                    "doc_method": "setup_nfs_client",
                    "group": "Bare Metal Host Actions",
                }
            ])
        
        # Add NFS specific actions for active hosts
        if self.status == "Active":
            if self.is_nfs_server:
                actions.append({
                    "action": "Optimize NFS Server",
                    "description": "Optimize NFS server for better performance",
                    "button_label": "Optimize NFS",
                    "condition": self.is_nfs_server,
                    "doc_method": "optimize_nfs_server",
                    "group": "NFS Server Actions",
                })
            
            actions.append({
                "action": "Check NFS Connectivity",
                "description": "Test NFS server connectivity",
                "button_label": "Check NFS",
                "condition": True,
                "doc_method": "check_nfs_connectivity",
                "group": "NFS Server Actions",
            })
        
        # Add server doctype and name to all actions
        for action in actions:
            action["server_doctype"] = self.doctype
            action["server_name"] = self.name
        
        return [action for action in actions if action.get("condition", True)]

    @frappe.whitelist()
    def ping_ansible(self):
        """
        Ping the host using Ansible
        """
        try:
            # Create a server-like object with the properties Ansible needs
            class ServerObj:
                def __init__(self, doc):
                    self.name = doc.name
                    self.ip = doc.ip
                    self.doctype = doc.doctype
            
            server_obj = ServerObj(self)
            
            ansible = Ansible(
                playbook="ping.yml",
                server=server_obj,
                user=self.ssh_user or "root",
                port=self.ssh_port or 22,
            )
            play = ansible.run()
            return f"Ping status: {play.status}"
        except Exception as e:
            log_error("Bare Metal Host Ping Exception", server=self.as_dict())
            return f"Ping failed: {str(e)}"

    @frappe.whitelist()
    def ping_ansible_unprepared(self):
        """
        Ping the unprepared host using Ansible
        """
        try:
            # Create a server-like object with the properties Ansible needs
            class ServerObj:
                def __init__(self, doc):
                    self.name = doc.name
                    self.ip = doc.ip
                    self.doctype = doc.doctype
            
            server_obj = ServerObj(self)
            
            ansible = Ansible(
                playbook="ping.yml",
                server=server_obj,
                user=self.ssh_user or "root",
                port=self.ssh_port or 22,
                password=self.frappe_user_password,
            )
            play = ansible.run()
            return f"Ping status: {play.status}"
        except Exception as e:
            log_error("Bare Metal Host Unprepared Ping Exception", server=self.as_dict())
            return f"Ping failed: {str(e)}"

    @frappe.whitelist()
    def setup_nfs_server(self):
        """
        Set up this host as an NFS server for VM storage
        """
        self.status = "Installing"
        self.save()
        frappe.enqueue_doc(self.doctype, self.name, "_setup_nfs_server", queue="long", timeout=1200)

    def _setup_nfs_server(self):
        try:
            class ServerObj:
                def __init__(self, doc):
                    self.name = doc.name
                    self.ip = doc.ip
                    self.doctype = doc.doctype
            
            server_obj = ServerObj(self)
            
            ansible = Ansible(
                playbook="nfs_server.yml",
                server=server_obj,
                user=self.ssh_user or "root",
                port=self.ssh_port or 22,
                variables={
                    "nfs_exports_directory": self.nfs_exports_directory,
                    "configure_firewall": True,
                    "optimize_nfs": True,
                    "nfs_rsize": 1048576,
                    "nfs_wsize": 1048576,
                    "nfs_threads": 16
                }
            )
            play = ansible.run()
            self.reload()
            if play.status == "Success":
                self.db_set("is_nfs_server", 1)
                self.db_set("status", "Active")
                frappe.msgprint("NFS server setup completed successfully")
            else:
                self.db_set("status", "Broken")
                frappe.throw(f"NFS server setup failed: {play.status}")
            return play
        except Exception as e:
            self.db_set("status", "Broken")
            log_error("NFS Server Setup Exception", server=self.as_dict(), error=str(e))
            frappe.throw(f"NFS server setup failed: {str(e)}")

    @frappe.whitelist()
    def optimize_nfs_server(self):
        """
        Optimize NFS server for better performance
        """
        if not self.is_nfs_server:
            frappe.throw("This host is not an NFS server. Please set it up as an NFS server first.")
            
        self.status = "Optimizing"
        self.save()
        frappe.enqueue_doc(self.doctype, self.name, "_optimize_nfs_server", queue="long", timeout=600)
    
    def _optimize_nfs_server(self):
        """Run ansible playbook to optimize NFS server settings"""
        try:
            class ServerObj:
                def __init__(self, doc):
                    self.name = doc.name
                    self.ip = doc.ip
                    self.doctype = doc.doctype
            
            server_obj = ServerObj(self)
            
            ansible = Ansible(
                playbook="nfs_server_optimize.yml",
                server=server_obj,
                user=self.ssh_user or "root",
                port=self.ssh_port or 22,
                variables={
                    "nfs_exports_directory": self.nfs_exports_directory,
                    "nfs_rsize": 1048576,
                    "nfs_wsize": 1048576,
                    "nfs_threads": 16,
                    "nfs_async": True
                }
            )
            play = ansible.run()
            self.reload()
            
            if play.status == "Success":
                self.db_set("status", "Active")
                frappe.msgprint("NFS server optimized successfully")
            else:
                self.db_set("status", "Broken")
                frappe.throw(f"NFS server optimization failed: {play.status}")
                
            return play
        except Exception as e:
            self.db_set("status", "Broken")
            log_error("NFS Server Optimization Exception", server=self.as_dict(), error=str(e))
            frappe.throw(f"NFS server optimization failed: {str(e)}")
            
    @frappe.whitelist()
    def check_nfs_connectivity(self):
        """
        Check NFS connectivity from client perspective
        """
        try:
            class ServerObj:
                def __init__(self, doc):
                    self.name = doc.name
                    self.ip = doc.ip
                    self.doctype = doc.doctype
            
            server_obj = ServerObj(self)
            
            # Get NFS server IP to test connectivity
            if self.is_nfs_server:
                nfs_server_ip = self.ip
            else:
                nfs_server_ip = frappe.db.get_single_value("Press Settings", "nfs_server")
                
            if not nfs_server_ip:
                frappe.throw("NFS server not configured")
                
            ansible = Ansible(
                playbook="nfs_connectivity_check.yml",
                server=server_obj,
                user=self.ssh_user or "root",
                port=self.ssh_port or 22,
                variables={
                    "nfs_server_ip": nfs_server_ip
                }
            )
            play = ansible.run()
            
            if play.status == "Success":
                frappe.msgprint("NFS connectivity check passed successfully")
                return True
            else:
                frappe.msgprint(f"NFS connectivity check failed: {play.status}")
                return False
        except Exception as e:
            log_error("NFS Connectivity Check Exception", server=self.as_dict(), error=str(e))
            frappe.throw(f"NFS connectivity check failed: {str(e)}")

    @frappe.whitelist()
    def setup_nfs_client(self):
        """
        Set up this host as an NFS client for VM storage
        """
        self.status = "Installing"
        self.save()
        frappe.enqueue_doc(self.doctype, self.name, "_setup_nfs_client", queue="long", timeout=1200)

    def _setup_nfs_client(self):
        try:
            class ServerObj:
                def __init__(self, doc):
                    self.name = doc.name
                    self.ip = doc.ip
                    self.doctype = doc.doctype
            
            server_obj = ServerObj(self)
            
            # Get NFS server details from settings
            nfs_server = frappe.db.get_single_value("Press Settings", "nfs_server")
            if not nfs_server:
                frappe.throw("NFS server not configured in Press Settings")
            
            ansible = Ansible(
                playbook="nfs_client.yml",
                server=server_obj,
                user=self.ssh_user or "root",
                port=self.ssh_port or 22,
                variables={
                    "nfs_server": nfs_server,
                    "nfs_mount_point": self.nfs_mount_point,
                    "nfs_mount_options": "rw,sync,hard,intr,noatime,nodiratime,rsize=1048576,wsize=1048576,vers=4.2",
                    "setup_automount": True,
                    "configure_health_check": True
                }
            )
            play = ansible.run()
            self.reload()
            if play.status == "Success":
                self.is_nfs_client = True
                self.save()
            return play
        except Exception as e:
            self.db_set("status", "Broken")
            log_error("NFS Client Setup Exception", server=self.as_dict(), error=str(e))
            frappe.throw(f"NFS client setup failed: {str(e)}")

    @frappe.whitelist()
    def setup_vm_host_with_nfs(self):
        """
        Set up server for KVM virtualization with NFS storage
        """
        # Validate required fields
        if not self.ip:
            frappe.throw("IP address is required")
        if not self.ssh_user:
            frappe.throw("SSH user is required")
        if not self.ssh_port:
            frappe.throw("SSH port is required")
        if not self.nfs_mount_point:
            frappe.throw("NFS mount point is required")
            
        # Check if server is prepared
        if not self.is_server_prepared:
            frappe.throw("Server must be prepared before setting up as VM host. Please run 'Prepare Server' first.")
            
        # Get NFS server details from settings
        nfs_server = frappe.db.get_single_value("Press Settings", "nfs_server")
        if not nfs_server:
            frappe.throw("NFS server not configured in Press Settings")
            
        # Update status and enqueue setup
        self.status = "Installing"
        self.save()
        frappe.enqueue_doc(self.doctype, self.name, "_setup_vm_host_with_nfs", queue="long", timeout=2400)

    def _setup_vm_host_with_nfs(self):
        """Run ansible playbook to set up KVM virtualization with NFS storage"""
        try:
            class ServerObj:
                def __init__(self, doc):
                    self.name = doc.name
                    self.ip = doc.ip
                    self.doctype = doc.doctype
            
            server_obj = ServerObj(self)
            
            # Get NFS server details from settings
            nfs_server = frappe.db.get_single_value("Press Settings", "nfs_server")
            if not nfs_server:
                frappe.throw("NFS server not configured in Press Settings")
            
            # Set up variables for the playbook
            variables = {
                "configure_network": True,
                "configure_storage": True,
                "configure_firewall": True,
                "configure_shared_storage": True,
                "setup_vm_storage": True,
                "optimize_io": True,
                "storage_path": "/var/lib/libvirt/images",
                "vm_directory": "/opt/vms",
                "vm_images_directory": "/opt/vm_images",
                "vm_config_directory": "/opt/vm_configs",
                "vm_templates_directory": "/opt/vm_templates",
                "nfs_server": nfs_server,
                "nfs_server_export": "/exports/vm_storage",
                "nfs_mount_point": self.nfs_mount_point,
                "shared_storage_pool_name": "shared_storage",
                "bridge_network": {
                    "name": "br0",
                    "ip": "192.168.100.1",
                    "netmask": "255.255.255.0",
                    "dhcp_start": "192.168.100.100",
                    "dhcp_end": "192.168.100.200"
                }
            }
            
            ansible = Ansible(
                playbook="bare_metal_vm_host_with_nfs.yml",
                server=server_obj,
                user=self.ssh_user or "root",
                port=self.ssh_port or 22,
                variables=variables
            )
            
            play = ansible.run()
            self.reload()
            
            if play.status == "Success":
                self.db_set("is_vm_host_setup", 1)
                self.db_set("is_vm_host", 1)  # Mark as VM host
                self.db_set("is_nfs_client", 1)
                self.db_set("status", "Active")
                frappe.msgprint("VM host setup with NFS completed successfully")
            else:
                self.db_set("status", "Broken")
                frappe.throw(f"VM host setup with NFS failed: {play.status}")
                
            return play
            
        except Exception as e:
            self.db_set("status", "Broken")
            log_error("VM Host with NFS Setup Exception", server=self.as_dict(), error=str(e))
            frappe.throw(f"VM host setup with NFS failed: {str(e)}") 