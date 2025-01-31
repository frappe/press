import frappe
from press.utils import get_current_team
from frappe.utils import cint, get_url

@frappe.whitelist()
def provision_bare_metal_vm(cluster, vcpu, memory, disk_size, image=None):
    """Create new VM on bare metal host"""
    if not cluster:
        frappe.throw("Cluster is required")

    # Validate cluster is bare metal type
    cluster_doc = frappe.get_doc("Cluster", cluster)
    if cluster_doc.cloud_provider != "Bare Metal":
        frappe.throw("Invalid cluster type")

    vm = frappe.get_doc({
        "doctype": "Virtual Machine",
        "cloud_provider": "Bare Metal",
        "cluster": cluster,
        "vcpu": cint(vcpu),
        "memory": cint(memory),
        "disk_size": cint(disk_size),
        "virtual_machine_image": image,
        "team": get_current_team()
    })
    vm.insert()
    vm.provision()
    return vm.name

@frappe.whitelist()
def setup_bare_metal_network(cluster):
    """Configure networking for VMs"""
    if not cluster:
        frappe.throw("Cluster is required")

    cluster_doc = frappe.get_doc("Cluster", cluster)
    if cluster_doc.cloud_provider != "Bare Metal":
        frappe.throw("Invalid cluster type")

    return cluster_doc.provision_on_bare_metal()

@frappe.whitelist()
def manage_bare_metal_storage(vm, operation, size=None):
    """Handle volume operations"""
    if not vm:
        frappe.throw("VM is required")

    vm_doc = frappe.get_doc("Virtual Machine", vm)
    if vm_doc.cloud_provider != "Bare Metal":
        frappe.throw("Invalid VM type")
    
    if operation == "resize":
        if not size:
            frappe.throw("Size is required for resize operation")
        return vm_doc.increase_disk_size(cint(size))
    elif operation == "snapshot":
        return vm_doc.create_snapshots()
    else:
        frappe.throw("Invalid operation")

@frappe.whitelist()
def monitor_bare_metal_host(host):
    """Track host resources and metrics"""
    if not host:
        frappe.throw("Host is required")

    host_doc = frappe.get_doc("Bare Metal Host", host)
    agent = host_doc.get_agent()
    return agent.get_metrics()

@frappe.whitelist()
def start_bare_metal_vm(vm):
    """Start a VM on bare metal host"""
    if not vm:
        frappe.throw("VM is required")

    vm_doc = frappe.get_doc("Virtual Machine", vm)
    if vm_doc.cloud_provider != "Bare Metal":
        frappe.throw("Invalid VM type")

    return vm_doc._start_bare_metal()

@frappe.whitelist()
def stop_bare_metal_vm(vm, force=False):
    """Stop a VM on bare metal host"""
    if not vm:
        frappe.throw("VM is required")

    vm_doc = frappe.get_doc("Virtual Machine", vm)
    if vm_doc.cloud_provider != "Bare Metal":
        frappe.throw("Invalid VM type")

    return vm_doc._stop_bare_metal(force=cint(force))

@frappe.whitelist()
def reboot_bare_metal_vm(vm):
    """Reboot a VM on bare metal host"""
    if not vm:
        frappe.throw("VM is required")

    vm_doc = frappe.get_doc("Virtual Machine", vm)
    if vm_doc.cloud_provider != "Bare Metal":
        frappe.throw("Invalid VM type")

    return vm_doc._reboot_bare_metal()

@frappe.whitelist()
def terminate_bare_metal_vm(vm):
    """Terminate a VM on bare metal host"""
    if not vm:
        frappe.throw("VM is required")

    vm_doc = frappe.get_doc("Virtual Machine", vm)
    if vm_doc.cloud_provider != "Bare Metal":
        frappe.throw("Invalid VM type")

    return vm_doc._terminate_bare_metal()

@frappe.whitelist()
def get_hosts():
    """Get all bare metal hosts for current team"""
    team = get_current_team()
    return frappe.get_all(
        "Bare Metal Host",
        filters={"cluster": ["in", frappe.get_all("Cluster", {"team": team}, pluck="name")]},
        fields=["name", "host_name", "ip_address", "status", "cluster",
                "total_cpu", "total_memory", "total_disk",
                "available_cpu", "available_memory", "available_disk"]
    )

@frappe.whitelist()
def get_host(name):
    """Get specific bare metal host details"""
    team = get_current_team()
    host = frappe.get_doc("Bare Metal Host", name)
    if host.cluster not in frappe.get_all("Cluster", {"team": team}, pluck="name"):
        frappe.throw("Not allowed to access this host")
    return host

@frappe.whitelist()
def get_vm_api_status():
    """Check if VM API is accessible"""
    try:
        host = frappe.new_doc("Bare Metal Host")
        host.check_api_connection()
        return {"status": "success", "message": "VM API is accessible"}
    except Exception as e:
        return {"status": "error", "message": str(e)} 