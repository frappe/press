import frappe
from frappe.model.document import Document
import yaml
import jinja2
from datetime import datetime
import ipaddress
import requests
import json

class BareMetalVM(Document):
    def validate(self):
        self.validate_network()
        if self.allow_custom_cloud_init:
            self.validate_cloud_init()
    
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
    
    def before_insert(self):
        """Set creation timestamp"""
        self.created_at = datetime.now()
    
    def get_cloud_init_config(self):
        """Get cloud-init configuration"""
        if self.allow_custom_cloud_init:
            return {
                'user_data': self.user_data,
                'meta_data': self.meta_data,
                'network_config': self.network_config
            }
        
        # Get configuration from template
        template = frappe.get_doc("Bare Metal VM Template", self.template)
        context = {
            'instance_id': self.name,
            'hostname': self.name,
            'ip_address': self.ip_address,
            'gateway': self.gateway,
            'netmask': self.netmask,
            'nameservers': [ns.strip() for ns in (self.nameservers or '').split('\n') if ns.strip()]
        }
        return template.render_templates(context)
    
    def create_vm(self):
        """Create VM on host"""
        host = frappe.get_doc("Bare Metal Host", self.host)
        template = frappe.get_doc("Bare Metal VM Template", self.template)
        
        # Prepare VM configuration
        vm_config = {
            'name': self.name,
            'cpu': self.cpu or template.default_cpu,
            'memory': self.memory or template.default_memory,
            'disk': self.disk or template.default_disk,
            'network': {
                'ip_address': self.ip_address,
                'gateway': self.gateway,
                'netmask': self.netmask,
                'nameservers': [ns.strip() for ns in (self.nameservers or '').split('\n') if ns.strip()]
            },
            'cloud_init': self.get_cloud_init_config()
        }
        
        # Call host API to create VM
        try:
            response = requests.post(
                f"{host.api_base_url}/vms",
                json=vm_config,
                headers={'Authorization': f'Bearer {host.api_key}'}
            )
            response.raise_for_status()
            
            # Update status
            self.status = "Running"
            self.started_at = datetime.now()
            self.save()
            
        except Exception as e:
            frappe.throw(f"Failed to create VM: {str(e)}")
    
    def start_vm(self):
        """Start VM"""
        if self.status == "Running":
            frappe.throw("VM is already running")
            
        host = frappe.get_doc("Bare Metal Host", self.host)
        
        try:
            response = requests.post(
                f"{host.api_base_url}/vms/{self.name}/start",
                headers={'Authorization': f'Bearer {host.api_key}'}
            )
            response.raise_for_status()
            
            # Update status
            self.status = "Running"
            self.started_at = datetime.now()
            self.save()
            
        except Exception as e:
            frappe.throw(f"Failed to start VM: {str(e)}")
    
    def stop_vm(self, force=False):
        """Stop VM"""
        if self.status != "Running":
            frappe.throw("VM is not running")
            
        host = frappe.get_doc("Bare Metal Host", self.host)
        
        try:
            response = requests.post(
                f"{host.api_base_url}/vms/{self.name}/stop",
                json={'force': force},
                headers={'Authorization': f'Bearer {host.api_key}'}
            )
            response.raise_for_status()
            
            # Update status
            self.status = "Stopped"
            self.stopped_at = datetime.now()
            self.save()
            
        except Exception as e:
            frappe.throw(f"Failed to stop VM: {str(e)}")
    
    def delete_vm(self):
        """Delete VM"""
        if self.status == "Running":
            frappe.throw("Cannot delete running VM. Stop it first.")
            
        host = frappe.get_doc("Bare Metal Host", self.host)
        
        try:
            response = requests.delete(
                f"{host.api_base_url}/vms/{self.name}",
                headers={'Authorization': f'Bearer {host.api_key}'}
            )
            response.raise_for_status()
            
            # Update status
            self.status = "Deleted"
            self.save()
            
        except Exception as e:
            frappe.throw(f"Failed to delete VM: {str(e)}")
    
    def on_trash(self):
        """Delete VM when document is deleted"""
        if self.status not in ["Deleted", "Creating"]:
            self.delete_vm() 