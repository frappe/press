# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

import frappe
import requests
import json
from frappe.model.document import Document
from datetime import datetime
from urllib.parse import urlparse
from jinja2 import Template

class BareMetalHost(Document):
    def validate(self):
        self.validate_resources()
        self.validate_api_url()
        self.initialize_resources()
        self.validate_cloud_init_templates()

    def validate_api_url(self):
        """Validate API URL format"""
        if not self.vm_api_url:
            frappe.throw("VM API URL is required")
        try:
            result = urlparse(self.vm_api_url)
            if not all([result.scheme, result.netloc]):
                frappe.throw("Invalid API URL format. Must include protocol and host")
        except Exception:
            frappe.throw("Invalid API URL format")

    def validate_cloud_init_templates(self):
        """Validate cloud-init templates"""
        if self.allow_custom_cloud_init:
            # Validate custom templates if provided
            if self.custom_user_data_template:
                self._validate_jinja_template(self.custom_user_data_template, "Custom User Data Template")
            if self.custom_meta_data_template:
                self._validate_jinja_template(self.custom_meta_data_template, "Custom Meta Data Template")
            if self.custom_network_config_template:
                self._validate_jinja_template(self.custom_network_config_template, "Custom Network Config Template")

    def _validate_jinja_template(self, template_str: str, template_name: str) -> None:
        """Validate Jinja2 template syntax"""
        try:
            Template(template_str)
        except Exception as e:
            frappe.throw(f"Invalid Jinja2 template in {template_name}: {str(e)}")

    def initialize_resources(self):
        """Initialize resource values if not set"""
        if not self.available_cpu:
            self.available_cpu = self.total_cpu
        if not self.available_memory:
            self.available_memory = self.total_memory
        if not self.available_disk:
            self.available_disk = self.total_disk

    def validate_resources(self):
        """Validate resource configurations"""
        if not self.total_cpu or self.total_cpu <= 0:
            frappe.throw("Total CPU must be greater than 0")
        if not self.total_memory or self.total_memory <= 0:
            frappe.throw("Total Memory must be greater than 0")
        if not self.total_disk or self.total_disk <= 0:
            frappe.throw("Total Disk must be greater than 0")

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

    def check_api_connection(self):
        """Check if VM API is accessible"""
        try:
            response = requests.get(
                f"{self.vm_api_url}/health",
                timeout=5,
                verify=True  # Enable SSL verification
            )
            response.raise_for_status()
            return True
        except requests.exceptions.SSLError:
            frappe.throw("SSL verification failed. Check the API URL and SSL certificate.")
        except requests.exceptions.ConnectionError:
            frappe.throw("Could not connect to API. Check if the service is running.")
        except requests.exceptions.Timeout:
            frappe.throw("API request timed out. Check the network connection.")
        except requests.exceptions.RequestException as e:
            frappe.throw(f"API connection failed: {str(e)}")

    def allocate_resources(self, cpu, memory, disk):
        """Allocate resources for a new VM"""
        if not all(isinstance(x, (int, float)) for x in [cpu, memory, disk]):
            frappe.throw("Resource values must be numbers")
            
        if cpu > self.available_cpu:
            frappe.throw(f"Not enough CPU available. Required: {cpu}, Available: {self.available_cpu}")
        if memory > self.available_memory:
            frappe.throw(f"Not enough memory available. Required: {memory}, Available: {self.available_memory}")
        if disk > self.available_disk:
            frappe.throw(f"Not enough disk space available. Required: {disk}, Available: {self.available_disk}")

        self.available_cpu = max(0, self.available_cpu - cpu)
        self.available_memory = max(0, self.available_memory - memory)
        self.available_disk = max(0, self.available_disk - disk)
        self.save()

    def deallocate_resources(self, cpu, memory, disk):
        """Release resources when a VM is deleted"""
        if not all(isinstance(x, (int, float)) for x in [cpu, memory, disk]):
            frappe.throw("Resource values must be numbers")
            
        self.available_cpu = min(self.total_cpu, self.available_cpu + cpu)
        self.available_memory = min(self.total_memory, self.available_memory + memory)
        self.available_disk = min(self.total_disk, self.available_disk + disk)
        self.save()

    def get_headers(self):
        """Get API headers with authentication"""
        api_key = self.get_password('vm_api_key')
        if not api_key:
            frappe.throw("VM API Key not set")
        return {
            "Authorization": f"Bearer {api_key}"
        }

    def get_cloud_init_config(self, vm_name: str, network_config: dict, custom_config: dict = None) -> dict:
        """Generate cloud-init configuration for a VM"""
        try:
            # Validate required network config
            if not network_config.get("ip_address"):
                frappe.throw("IP address is required in network configuration")
            if not network_config.get("gateway"):
                frappe.throw("Gateway is required in network configuration")

            # Base context with defaults
            context = {
                "instance_id": vm_name,
                "hostname": vm_name,
                "ip_address": network_config.get("ip_address"),
                "gateway": network_config.get("gateway"),
                "netmask": network_config.get("netmask", "255.255.255.0"),
                "nameservers": network_config.get("nameservers", ["8.8.8.8", "8.8.4.4"]),
                "ssh_authorized_keys": network_config.get("ssh_keys", []),
                "timezone": network_config.get("timezone", "UTC"),
                "ntp_servers": network_config.get("ntp_servers", ["pool.ntp.org"]),
                "packages": [
                    "net-tools",
                    "iproute2",
                    "iptables",
                    "netcat",
                    "curl",
                    "wget",
                    "vim"
                ]
            }

            # Merge custom config if provided
            if custom_config:
                # Deep merge for nested structures
                for key, value in custom_config.items():
                    if isinstance(value, dict) and key in context and isinstance(context[key], dict):
                        context[key].update(value)
                    elif isinstance(value, list) and key in context and isinstance(context[key], list):
                        context[key].extend(value)
                    else:
                        context[key] = value

            # Generate configurations
            try:
                if self.allow_custom_cloud_init and custom_config:
                    user_data = Template(self.custom_user_data_template or self.default_user_data).render(**context)
                    meta_data = Template(self.custom_meta_data_template or self.default_meta_data).render(**context)
                    network_conf = Template(self.custom_network_config_template or self.default_network_config).render(**context)
                else:
                    user_data = Template(self.default_user_data).render(**context)
                    meta_data = Template(self.default_meta_data).render(**context)
                    network_conf = Template(self.default_network_config).render(**context)

                # Validate generated YAML
                import yaml
                for name, data in [
                    ("user_data", user_data),
                    ("meta_data", meta_data),
                    ("network_config", network_conf)
                ]:
                    try:
                        yaml.safe_load(data)
                    except yaml.YAMLError as e:
                        frappe.throw(f"Invalid YAML in {name}: {str(e)}")

                return {
                    "user_data": user_data,
                    "meta_data": meta_data,
                    "network_config": network_conf,
                    "context": context  # Include rendered context for debugging
                }

            except Exception as e:
                frappe.log_error(f"Template rendering error: {str(e)}")
                frappe.throw(f"Failed to render cloud-init templates: {str(e)}")

        except Exception as e:
            frappe.log_error(f"Error generating cloud-init config: {str(e)}")
            frappe.throw(f"Failed to generate cloud-init configuration: {str(e)}")

    def setup_network(self, name, ip_range, subnets):
        """Create network via VM experiments API"""
        if not name or not ip_range or not subnets:
            frappe.throw("Name, IP range and subnets are required")
            
        try:
            response = requests.post(
                f"{self.vm_api_url}/api/networks",
                json={
                    "name": name,
                    "cidr": ip_range,
                    "subnets": subnets
                },
                timeout=5,
                verify=True
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            frappe.log_error(f"Network setup failed: {str(e)}")
            frappe.throw("Failed to setup network. Check the error log for details.")

    def create_vm(self, name: str, network_id: str, cloud_init_config: dict = None, **kwargs):
        """Create VM via VM experiments API"""
        try:
            # Allocate resources first
            self.allocate_resources(
                kwargs.get('cpu', 1),
                kwargs.get('memory', 1024),
                kwargs.get('disk', 20)
            )

            # Generate cloud-init config if not provided
            if not cloud_init_config:
                cloud_init_config = self.get_cloud_init_config(
                    name,
                    kwargs.get('network_config', {})
                )

            response = requests.post(
                f"{self.vm_api_url}/api/vms",
                headers=self.get_headers(),
                json={
                    "name": name,
                    "network": network_id,
                    "cpu": kwargs.get('cpu', 1),
                    "memory": kwargs.get('memory', 1024),
                    "disk": kwargs.get('disk', 20),
                    "cloud_init": cloud_init_config,
                    "created_at": datetime.now().isoformat(),
                    **kwargs
                },
                timeout=30  # Longer timeout for VM creation
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            # Deallocate resources on failure
            self.deallocate_resources(
                kwargs.get('cpu', 1),
                kwargs.get('memory', 1024),
                kwargs.get('disk', 20)
            )
            frappe.throw(f"Failed to create VM: {str(e)}")

    def start_vm(self, name):
        """Start a VM"""
        try:
            response = requests.post(
                f"{self.vm_api_url}/api/vms/{name}/start",
                headers=self.get_headers(),
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            frappe.throw(f"Failed to start VM: {str(e)}")

    def stop_vm(self, name, force=False):
        """Stop a VM"""
        try:
            response = requests.post(
                f"{self.vm_api_url}/api/vms/{name}/stop",
                headers=self.get_headers(),
                json={"force": force},
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            frappe.throw(f"Failed to stop VM: {str(e)}")

    def delete_vm(self, name):
        """Delete a VM"""
        try:
            response = requests.delete(
                f"{self.vm_api_url}/api/vms/{name}",
                headers=self.get_headers(),
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            frappe.throw(f"Failed to delete VM: {str(e)}")

    def get_vm(self, name):
        """Get VM status"""
        if not name:
            frappe.throw("VM name is required")
            
        try:
            response = requests.get(
                f"{self.vm_api_url}/api/vms/{name}",
                timeout=5,
                verify=True
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            frappe.log_error(f"Failed to get VM status: {str(e)}")
            return None 