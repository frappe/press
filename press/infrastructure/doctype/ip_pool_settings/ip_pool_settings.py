import frappe
from frappe.model.document import Document
from datetime import datetime

class IPPoolSettings(Document):
    def validate(self):
        if self.auto_scaling_enabled and not self.max_pool_size:
            frappe.throw("Maximum Pool Size is required when Auto Scaling is enabled")
        
        if self.scaling_threshold < 50 or self.scaling_threshold > 95:
            frappe.throw("Scaling Threshold must be between 50% and 95%")

    def check_and_scale(self):
        """Check utilization and scale if needed"""
        if not self.auto_scaling_enabled:
            return

        utilization = (self.used_ips / self.total_ips * 100) if self.total_ips > 0 else 0
        
        if utilization >= self.scaling_threshold:
            self.scale_pool()

    def scale_pool(self):
        """Scale the IP pool"""
        if self.total_ips >= self.max_pool_size:
            frappe.log_error(
                "IP Pool reached maximum size",
                "IP Pool Auto Scaling"
            )
            return

        try:
            # Calculate new size (20% increase)
            increase = max(int(self.total_ips * 0.2), 10)
            new_size = min(self.total_ips + increase, self.max_pool_size)
            
            # Implement the actual scaling logic here
            # This would typically involve cloud provider API calls
            # For now, we just update the numbers
            self.total_ips = new_size
            self.last_scaled_at = datetime.now()
            self.save()
            
            frappe.log_error(
                f"IP Pool scaled from {self.total_ips - increase} to {self.total_ips}",
                "IP Pool Auto Scaling"
            )
        except Exception as e:
            frappe.log_error(
                f"IP Pool scaling failed: {str(e)}",
                "IP Pool Auto Scaling"
            )

def update_ip_metrics():
    """Scheduled job to update IP metrics"""
    settings = frappe.get_single("IP Pool Settings")
    if not settings:
        return

    try:
        # Get metrics from VM system
        vm_metrics = frappe.get_value(
            "Virtual Machine Settings",
            None,
            ["total_ips", "used_ips", "elastic_ips"]
        ) or (0, 0, 0)

        settings.total_ips = vm_metrics[0]
        settings.used_ips = vm_metrics[1]
        settings.elastic_ips = vm_metrics[2]
        settings.last_updated = datetime.now()
        
        # Check if we need to scale
        settings.check_and_scale()
        
        settings.save()
    except Exception as e:
        frappe.log_error(
            f"Failed to update IP metrics: {str(e)}",
            "IP Pool Metrics"
        ) 