# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

import frappe
import ipaddress
from frappe.model.document import Document

class BareMetalFirewallRule(Document):
    def validate(self):
        self.validate_ports()
        self.validate_cidr()

    def validate_ports(self):
        """Validate port configuration"""
        if self.protocol not in ['tcp', 'udp', 'icmp', 'all']:
            frappe.throw('Invalid protocol')

        if self.protocol in ['tcp', 'udp', 'all']:
            if not self.from_port:
                frappe.throw('From Port is required for TCP/UDP protocols')
            if not self.to_port:
                frappe.throw('To Port is required for TCP/UDP protocols')
            
            try:
                from_port = int(self.from_port)
                to_port = int(self.to_port)
                
                if from_port < 0 or from_port > 65535:
                    frappe.throw('From Port must be between 0 and 65535')
                if to_port < 0 or to_port > 65535:
                    frappe.throw('To Port must be between 0 and 65535')
                if from_port > to_port:
                    frappe.throw('From Port cannot be greater than To Port')
            except (TypeError, ValueError):
                frappe.throw('Ports must be valid numbers')
        elif self.protocol == 'icmp':
            self.from_port = None
            self.to_port = None

    def validate_cidr(self):
        """Validate CIDR format"""
        if not self.source:
            frappe.throw('Source/Destination CIDR is required')
        
        try:
            network = ipaddress.ip_network(self.source)
            if network.prefixlen < 0 or network.prefixlen > 32:
                frappe.throw('Invalid CIDR subnet mask. Must be between 0 and 32')
        except ValueError:
            frappe.throw('Invalid CIDR format. Must be in format: x.x.x.x/y') 