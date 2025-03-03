import frappe
from frappe.model.document import Document
import yaml
import jinja2
from datetime import datetime
import ipaddress
import requests
import json
from frappe.utils import now_datetime
from press.infrastructure.api import VMExperimentsAdapter

class BareMetalVM(Document):
    def validate(self):
        self.validate_network()
        if self.allow_custom_cloud_init:
            self.validate_cloud_init()
        self.validate_resource_allocation()
    
    def validate_network(self):
        """Validate network configuration"""
        try:
            # Validate IP address
            ip = ipaddress.ip_address(self.ip_address)
            
            # Validate gateway
            gateway = ipaddress.ip_address(self.gateway)
            
            # Validate netmask
            netmask = ipaddress.ip_address(self.netmask)
            
            # Validate nameservers
            if self.nameservers:
                for ns in self.nameservers.split('\n'):
                    if ns.strip():
                        ipaddress.ip_address(ns.strip())
                        
        except ValueError as e:
            frappe.throw(f"Invalid network configuration: {str(e)}")
    
    def validate_cloud_init(self):
        """Validate cloud-init configuration"""
        if not self.allow_custom_cloud_init:
            return
            
        templates = {
            'user_data': self.user_data,
            'network_config': self.network_config
        }
        
        for name, content in templates.items():
            if not content:
                continue
                
            try:
                yaml.safe_load(content)
            except yaml.YAMLError as e:
                frappe.throw(f"Invalid YAML in {name}: {str(e)}")
    
    def validate_resource_allocation(self):
        """Validate resource allocation values"""
        if self.cpu <= 0:
            frappe.throw("CPU count must be greater than 0")
        if self.memory <= 0:
            frappe.throw("Memory must be greater than 0")
        if self.disk <= 0:
            frappe.throw("Disk size must be greater than 0")
    
    def before_insert(self):
        """Set default values before insert"""
        if not self.created_at:
            self.created_at = now_datetime()
        
        if not self.status:
            self.status = "Creating"
            
    def after_insert(self):
        """Trigger VM creation in VM Experiments after document insert"""
        if not frappe.flags.in_import and not frappe.flags.in_install:
            self.trigger_vm_creation()
    
    def trigger_vm_creation(self):
        """Create the VM in VM Experiments"""
        try:
            adapter = VMExperimentsAdapter()
            
            # Prepare network config
            network_config = {}
            if self.ip_address:
                network_config = {
                    "ip_address": self.ip_address,
                    "gateway": self.gateway,
                    "netmask": self.netmask,
                    "nameservers": [ns.strip() for ns in (self.nameservers or "").split(",") if ns.strip()]
                }
            
            # Prepare cloud-init config
            cloud_init_config = {}
            if self.template:
                template_doc = frappe.get_doc("Bare Metal VM Template", self.template)
                cloud_init_config = {
                    "context": {
                        "hostname": self.name,
                        "timezone": template_doc.timezone,
                        "packages": template_doc.packages.split("\n") if template_doc.packages else [],
                        "ssh_authorized_keys": template_doc.ssh_keys.split("\n") if template_doc.ssh_keys else []
                    }
                }
            
            # Override with custom cloud-init if allowed
            if self.allow_custom_cloud_init:
                if self.user_data:
                    cloud_init_config["user_data"] = self.user_data
                if self.meta_data:
                    cloud_init_config["meta_data"] = self.meta_data
                if self.network_config:
                    cloud_init_config["network_config"] = self.network_config
            
            # Prepare VM data
            vm_data = {
                "name": self.name,
                "host": self.host,
                "cpu": self.cpu,
                "memory": self.memory,
                "disk": self.disk,
                "network": network_config,
                "cloud_init": cloud_init_config
            }
            
            # Call VM Experiments API to create VM
            result = adapter.create_vm(vm_data)
            
            # Update status if successful
            if result.get("message"):
                self.status = "Creating"
                self.db_update()
                frappe.db.commit()
                
        except Exception as e:
            frappe.log_error(f"Failed to create VM in VM Experiments: {str(e)}", "BareMetalVM.trigger_vm_creation")
            
    def on_update(self):
        """Handle actions on update"""
        # Status change handling
        if self.has_value_changed("status"):
            if self.status == "Running" and not self.started_at:
                self.started_at = now_datetime()
            elif self.status == "Stopped" and not self.stopped_at:
                self.stopped_at = now_datetime()
                
    def start(self):
        """Start the VM"""
        try:
            if self.status == "Running":
                frappe.throw("VM is already running")
                
            adapter = VMExperimentsAdapter()
            result = adapter.start_vm(self.name)
            
            self.status = "Running"
            self.started_at = now_datetime()
            self.save()
            
            return result
            
        except Exception as e:
            frappe.log_error(f"Failed to start VM: {str(e)}", "BareMetalVM.start")
            raise
            
    def stop(self):
        """Stop the VM"""
        try:
            if self.status != "Running":
                frappe.throw("VM is not running")
                
            adapter = VMExperimentsAdapter()
            result = adapter.stop_vm(self.name)
            
            self.status = "Stopped"
            self.stopped_at = now_datetime()
            self.save()
            
            return result
            
        except Exception as e:
            frappe.log_error(f"Failed to stop VM: {str(e)}", "BareMetalVM.stop")
            raise
            
    def force_stop(self):
        """Force stop the VM"""
        try:
            if self.status != "Running":
                frappe.throw("VM is not running")
                
            adapter = VMExperimentsAdapter()
            result = adapter.force_stop_vm(self.name)
            
            self.status = "Stopped"
            self.stopped_at = now_datetime()
            self.save()
            
            return result
            
        except Exception as e:
            frappe.log_error(f"Failed to force stop VM: {str(e)}", "BareMetalVM.force_stop")
            raise
            
    def delete_vm(self):
        """Delete the VM"""
        try:
            adapter = VMExperimentsAdapter()
            result = adapter.delete_vm(self.name)
            
            self.status = "Deleted"
            self.save()
            
            return result
            
        except Exception as e:
            frappe.log_error(f"Failed to delete VM: {str(e)}", "BareMetalVM.delete_vm")
            raise
            
    def refresh_status(self):
        """Refresh VM status from VM Experiments"""
        try:
            adapter = VMExperimentsAdapter()
            vm_data = adapter.get_vm(self.name)
            
            if vm_data:
                status = vm_data.get("status")
                if status and status != self.status:
                    self.status = status
                    
                    # Update timestamps based on status
                    if self.status == "Running" and not self.started_at:
                        self.started_at = now_datetime()
                    elif self.status == "Stopped" and not self.stopped_at:
                        self.stopped_at = now_datetime()
                    
                    self.save()
                
            return vm_data
            
        except Exception as e:
            frappe.log_error(f"Failed to refresh VM status: {str(e)}", "BareMetalVM.refresh_status")
            
@frappe.whitelist()
def vm_action(vm_name, action):
    """
    Execute action on VM
    
    Args:
        vm_name: Name of the VM
        action: Action to perform (start, stop, force_stop, delete, refresh)
        
    Returns:
        dict: Result of the action
    """
    if not frappe.db.exists("Bare Metal VM", vm_name):
        frappe.throw(f"VM {vm_name} not found")
        
    vm = frappe.get_doc("Bare Metal VM", vm_name)
    
    if action == "start":
        return vm.start()
    elif action == "stop":
        return vm.stop()
    elif action == "force_stop":
        return vm.force_stop()
    elif action == "delete":
        return vm.delete_vm()
    elif action == "refresh":
        return vm.refresh_status()
    else:
        frappe.throw(f"Invalid action: {action}") 