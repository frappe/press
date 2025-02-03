import frappe
import requests
from frappe.model.document import Document
from datetime import datetime

class BareMetalHost(Document):
    def validate(self):
        self.validate_resources()
        self.check_api_connection()
        if not self.available_cpu:
            self.available_cpu = self.total_cpu
        if not self.available_memory:
            self.available_memory = self.total_memory
        if not self.available_disk:
            self.available_disk = self.total_disk

    def check_api_connection(self):
        """Check if VM API is accessible"""
        try:
            response = requests.get(
                f"{self.vm_api_url}/health",
                timeout=self.vm_api_timeout
            )
            response.raise_for_status()
        except Exception as e:
            frappe.throw(f"VM API not accessible at {self.vm_api_url}: {str(e)}")

    def validate_resources(self):
        if self.available_cpu > self.total_cpu:
            frappe.throw("Available CPU cannot be more than total CPU")
        if self.available_memory > self.total_memory:
            frappe.throw("Available memory cannot be more than total memory")
        if self.available_disk > self.total_disk:
            frappe.throw("Available disk cannot be more than total disk")

    def allocate_resources(self, cpu, memory, disk):
        """Allocate resources for a new VM"""
        if cpu > self.available_cpu:
            frappe.throw(f"Not enough CPU available. Required: {cpu}, Available: {self.available_cpu}")
        if memory > self.available_memory:
            frappe.throw(f"Not enough memory available. Required: {memory}, Available: {self.available_memory}")
        if disk > self.available_disk:
            frappe.throw(f"Not enough disk space available. Required: {disk}, Available: {self.available_disk}")

        self.available_cpu -= cpu
        self.available_memory -= memory
        self.available_disk -= disk
        self.save()

    def deallocate_resources(self, cpu, memory, disk):
        """Release resources when a VM is deleted"""
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

    def setup_network(self, name, ip_range, subnets):
        """Create network via VM experiments API"""
        try:
            response = requests.post(
                f"{self.vm_api_url}/api/networks",
                headers=self.get_headers(),
                json={
                    "name": name,
                    "cidr": ip_range,
                    "subnets": subnets
                },
                timeout=self.vm_api_timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            frappe.throw("Network creation timed out")
        except Exception as e:
            frappe.throw(f"Failed to setup network: {str(e)}")

    def create_vm(self, name, network_id, **kwargs):
        """Create VM via VM experiments API"""
        try:
            # Allocate resources first
            self.allocate_resources(
                kwargs.get('cpu', 1),
                kwargs.get('memory', 1024),
                kwargs.get('disk', 20)
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
                    "created_at": datetime.now().isoformat(),
                    **kwargs
                },
                timeout=self.vm_api_timeout
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
                timeout=self.vm_api_timeout
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
                timeout=self.vm_api_timeout
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
                timeout=self.vm_api_timeout
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            frappe.throw(f"Failed to delete VM: {str(e)}")

    def get_vm(self, name):
        """Get VM status"""
        try:
            response = requests.get(
                f"{self.vm_api_url}/api/vms/{name}",
                headers=self.get_headers(),
                timeout=self.vm_api_timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            frappe.log_error("VM status check timed out")
            return None
        except Exception as e:
            frappe.log_error(f"Failed to get VM status: {str(e)}")
            return None 