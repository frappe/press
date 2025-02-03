# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

import frappe
import ipaddress
import json
from frappe.model.document import Document
from datetime import datetime

class BareMetalVPC(Document):
    def validate(self):
        self.validate_cidr()
        if not self.used_private_ips:
            self.used_private_ips = json.dumps([])
        if not self.used_public_ips:
            self.used_public_ips = json.dumps([])

    def validate_cidr(self):
        try:
            ipaddress.ip_network(self.cidr)
        except ValueError as e:
            frappe.throw(f"Invalid CIDR format: {str(e)}")

    def _get_next_available_ip(self, network: str, used_ips: list) -> str:
        """Get next available IP from the network"""
        try:
            net = ipaddress.ip_network(network)
            # Skip the first IP (network address) and last IP (broadcast)
            for ip in list(net.hosts())[1:-1]:
                ip_str = str(ip)
                if ip_str not in used_ips:
                    return ip_str
            frappe.throw(f"No available IPs in network {network}")
        except Exception as e:
            frappe.throw(f"Error allocating IP from network {network}: {str(e)}")

    def allocate_ip(self) -> dict:
        """Allocate a new IP address pair (public and private) for a VM"""
        try:
            used_private = json.loads(self.used_private_ips)
            used_public = json.loads(self.used_public_ips)

            private_ip = self._get_next_available_ip(self.cidr, used_private)
            public_ip = self._get_next_available_ip("172.16.0.0/24", used_public)

            used_private.append(private_ip)
            used_public.append(public_ip)

            self.used_private_ips = json.dumps(used_private)
            self.used_public_ips = json.dumps(used_public)
            self.save()

            return {
                "private_ip": private_ip,
                "public_ip": public_ip,
                "allocated_at": datetime.now().isoformat()
            }
        except Exception as e:
            frappe.throw(f"Error allocating IP pair: {str(e)}")

    def release_ip(self, private_ip: str, public_ip: str) -> None:
        """Release allocated IP addresses back to the pool"""
        try:
            used_private = json.loads(self.used_private_ips)
            used_public = json.loads(self.used_public_ips)

            if private_ip in used_private:
                used_private.remove(private_ip)
            if public_ip in used_public:
                used_public.remove(public_ip)

            self.used_private_ips = json.dumps(used_private)
            self.used_public_ips = json.dumps(used_public)
            self.save()
        except Exception as e:
            frappe.throw(f"Error releasing IPs: {str(e)}")

    def on_trash(self):
        """Cleanup when VPC is deleted"""
        self.status = "Deleted"
        self.save() 