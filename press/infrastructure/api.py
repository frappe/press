import frappe
import requests
import json
import logging
from typing import Dict, List, Optional, Any
from frappe.utils import now_datetime, get_datetime

# Configure logging
logger = logging.getLogger(__name__)

class VMExperimentsAdapter:
    """API Adapter for VM Experiments integration with Press"""
    
    def __init__(self, base_url: str = None):
        """Initialize the adapter with VM Experiments API URL"""
        self.base_url = base_url or frappe.conf.get("vm_experiments_url", "http://localhost:5000")
        self.session = requests.Session()
        
    def _request(self, method: str, endpoint: str, data: Dict = None) -> Dict:
        """Execute request to VM Experiments API"""
        # Add '/api' prefix to all endpoints
        api_endpoint = f"/api{endpoint}" if not endpoint.startswith("/api") else endpoint
        url = f"{self.base_url}{api_endpoint}"
        headers = {"Content-Type": "application/json"}
        
        try:
            if method == "GET":
                response = self.session.get(url, headers=headers, timeout=10)
            elif method == "POST":
                response = self.session.post(url, json=data, headers=headers, timeout=10)
            elif method == "PUT":
                response = self.session.put(url, json=data, headers=headers, timeout=10)
            elif method == "DELETE":
                response = self.session.delete(url, headers=headers, timeout=10)
            else:
                raise ValueError(f"Unsupported method: {method}")
                
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"VM Experiments API error: {str(e)}")
            frappe.log_error(f"VM Experiments API error: {str(e)}", "VMExperimentsAdapter")
            raise
    
    def list_hosts(self) -> List[Dict]:
        """List all available hosts"""
        return self._request("GET", "/hosts")
    
    def get_host(self, host_id: str) -> Dict:
        """Get host details"""
        return self._request("GET", f"/hosts/{host_id}")
    
    def list_vms(self) -> Dict:
        """List all VMs"""
        return self._request("GET", "/vms")
    
    def get_vm(self, vm_id: str) -> Dict:
        """Get VM details"""
        return self._request("GET", f"/vms/{vm_id}")
    
    def create_vm(self, vm_data: Dict) -> Dict:
        """Create a new VM"""
        return self._request("POST", "/vms", vm_data)
    
    def start_vm(self, vm_id: str) -> Dict:
        """Start a VM"""
        return self._request("POST", f"/vms/{vm_id}/start")
    
    def stop_vm(self, vm_id: str) -> Dict:
        """Stop a VM"""
        return self._request("POST", f"/vms/{vm_id}/stop")
    
    def force_stop_vm(self, vm_id: str) -> Dict:
        """Force stop a VM"""
        return self._request("POST", f"/vms/{vm_id}/force-stop")
    
    def delete_vm(self, vm_id: str) -> Dict:
        """Delete a VM"""
        return self._request("DELETE", f"/vms/{vm_id}/delete")
    
    def get_network(self, network_id: str) -> Dict:
        """Get network details"""
        return self._request("GET", f"/networks/{network_id}")
    
    def list_networks(self) -> List[Dict]:
        """List all networks"""
        return self._request("GET", "/networks")
    
    def allocate_ip(self, network_id: str) -> Dict:
        """Allocate IP from network"""
        return self._request("POST", f"/networks/{network_id}/ips")
    
    def release_ip(self, network_id: str, ip: str) -> Dict:
        """Release IP back to network"""
        return self._request("DELETE", f"/networks/{network_id}/ips/{ip}")
    
    def get_ip_pool_metrics(self) -> Dict:
        """Get IP pool metrics"""
        return self._request("GET", "/api/ip-pool/metrics")
    
    def generate_cloud_init(self, config: Dict) -> Dict:
        """Generate cloud-init configuration"""
        return self._request("POST", "/cloud-init/generate", config)


def create_bare_metal_vm(vm_name: str, host: str, cpu: int, memory: int, disk: int, 
                        network_id: str = None, template: str = None) -> Dict:
    """
    Create a new bare metal VM through the VM Experiments API
    
    Args:
        vm_name: Name of the VM
        host: Host ID or name
        cpu: Number of CPUs
        memory: Memory in MB
        disk: Disk size in GB
        network_id: Network ID
        template: Template name
        
    Returns:
        Dict: The created VM details
    """
    try:
        adapter = VMExperimentsAdapter()
        
        # If network ID is provided, allocate IP
        ip_config = {}
        if network_id:
            network = adapter.get_network(network_id)
            ip_allocation = adapter.allocate_ip(network_id)
            ip_config = {
                "ip_address": ip_allocation["ip"],
                "gateway": network.get("gateway"),
                "netmask": network.get("netmask", "255.255.255.0"),
                "nameservers": network.get("nameservers", ["8.8.8.8", "8.8.4.4"])
            }
        
        # Generate cloud-init config if template is provided
        cloud_init_config = {}
        if template:
            template_doc = frappe.get_doc("Bare Metal VM Template", template)
            cloud_init_config = {
                "context": {
                    "hostname": vm_name,
                    "timezone": template_doc.timezone,
                    "packages": template_doc.packages.split("\n") if template_doc.packages else [],
                    "ssh_authorized_keys": template_doc.ssh_keys.split("\n") if template_doc.ssh_keys else []
                }
            }
            cloud_init = adapter.generate_cloud_init(cloud_init_config)
        
        # Create VM
        vm_data = {
            "name": vm_name,
            "host": host,
            "cpu": cpu,
            "memory": memory,
            "disk": disk,
            "network": {
                "id": network_id,
                **ip_config
            },
            "cloud_init": cloud_init_config
        }
        
        # Call VM Experiments API to create VM
        vm = adapter.create_vm(vm_data)
        
        # Create Bare Metal VM document in Press
        press_vm = frappe.new_doc("Bare Metal VM")
        press_vm.name = vm_name
        press_vm.host = host
        press_vm.status = "Creating"
        press_vm.template = template
        press_vm.cpu = cpu
        press_vm.memory = memory
        press_vm.disk = disk
        
        # Set network details
        if ip_config:
            press_vm.ip_address = ip_config.get("ip_address")
            press_vm.gateway = ip_config.get("gateway")
            press_vm.netmask = ip_config.get("netmask")
            press_vm.nameservers = ", ".join(ip_config.get("nameservers", []))
        
        # Set timestamps
        press_vm.created_at = now_datetime()
        
        # Save the document
        press_vm.insert()
        
        return {
            "press_vm": press_vm.as_dict(),
            "vm_experiments_vm": vm
        }
    
    except Exception as e:
        frappe.log_error(f"Failed to create bare metal VM: {str(e)}", "create_bare_metal_vm")
        raise


@frappe.whitelist()
def vm_action(vm_name: str, action: str) -> Dict:
    """
    Perform action on a VM
    
    Args:
        vm_name: Name of the VM
        action: Action to perform (start, stop, force_stop, delete)
    
    Returns:
        Dict: Result of the action
    """
    try:
        # Validate VM exists
        if not frappe.db.exists("Bare Metal VM", vm_name):
            frappe.throw(f"VM {vm_name} not found")
            
        vm = frappe.get_doc("Bare Metal VM", vm_name)
        adapter = VMExperimentsAdapter()
        
        result = {}
        if action == "start":
            result = adapter.start_vm(vm_name)
            vm.status = "Running"
            vm.started_at = now_datetime()
        elif action == "stop":
            result = adapter.stop_vm(vm_name)
            vm.status = "Stopped"
            vm.stopped_at = now_datetime()
        elif action == "force_stop":
            result = adapter.force_stop_vm(vm_name)
            vm.status = "Stopped"
            vm.stopped_at = now_datetime()
        elif action == "delete":
            result = adapter.delete_vm(vm_name)
            vm.status = "Deleted"
        else:
            frappe.throw(f"Invalid action: {action}")
        
        vm.save()
        return {
            "press_vm": vm.as_dict(),
            "result": result
        }
        
    except Exception as e:
        frappe.log_error(f"Failed to perform VM action: {str(e)}", "vm_action")
        raise


@frappe.whitelist()
def sync_bare_metal_vms():
    """
    Synchronize VM status between VM Experiments and Press
    """
    try:
        adapter = VMExperimentsAdapter()
        vms = adapter.list_vms()
        
        updated = []
        for vm_id, vm_data in vms.items():
            if frappe.db.exists("Bare Metal VM", vm_id):
                press_vm = frappe.get_doc("Bare Metal VM", vm_id)
                
                # Update status
                if vm_data.get("status") != press_vm.status:
                    press_vm.status = vm_data.get("status", press_vm.status)
                    
                    # Update timestamps based on status
                    if press_vm.status == "Running" and not press_vm.started_at:
                        press_vm.started_at = now_datetime()
                    elif press_vm.status == "Stopped" and not press_vm.stopped_at:
                        press_vm.stopped_at = now_datetime()
                    
                    press_vm.save()
                    updated.append(vm_id)
        
        return {
            "updated": updated,
            "total": len(vms)
        }
    
    except Exception as e:
        frappe.log_error(f"Failed to sync bare metal VMs: {str(e)}", "sync_bare_metal_vms")
        raise


def update_ip_pool_metrics():
    """
    Update IP Pool metrics from VM Experiments
    """
    try:
        adapter = VMExperimentsAdapter()
        metrics = adapter.get_ip_pool_metrics()
        
        if not frappe.db.exists("IP Pool Settings", "IP Pool Settings"):
            settings = frappe.new_doc("IP Pool Settings")
            settings.name = "IP Pool Settings"
        else:
            settings = frappe.get_doc("IP Pool Settings", "IP Pool Settings")
        
        settings.total_ips = metrics.get("total_ips", 0)
        settings.used_ips = metrics.get("used_ips", 0)
        settings.elastic_ips = metrics.get("elastic_ips", 0)
        settings.last_updated = now_datetime()
        
        # Check for auto-scaling
        if settings.auto_scaling_enabled:
            utilization = (settings.used_ips / settings.total_ips * 100) if settings.total_ips > 0 else 0
            if utilization >= settings.scaling_threshold:
                settings.check_and_scale()
        
        settings.save()
        
        return {
            "settings": settings.as_dict(),
            "metrics": metrics
        }
        
    except Exception as e:
        frappe.log_error(f"Failed to update IP pool metrics: {str(e)}", "update_ip_pool_metrics")
        raise 