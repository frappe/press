# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class BareMetalFirewallRule(Document):
    def validate(self):
        if self.protocol != 'icmp':
            if not self.from_port:
                frappe.throw('From Port is required for non-ICMP protocols')
            if not self.to_port:
                frappe.throw('To Port is required for non-ICMP protocols')
            if self.from_port < 0 or self.from_port > 65535:
                frappe.throw('From Port must be between 0 and 65535')
            if self.to_port < 0 or self.to_port > 65535:
                frappe.throw('To Port must be between 0 and 65535')
            if self.from_port > self.to_port:
                frappe.throw('From Port cannot be greater than To Port')

        # Validate CIDR format
        if not self.source:
            frappe.throw('Source/Destination CIDR is required')
        
        try:
            ip, subnet = self.source.split('/')
            subnet = int(subnet)
            if subnet < 0 or subnet > 32:
                frappe.throw('Invalid CIDR subnet mask. Must be between 0 and 32')
            
            # Validate IP format
            octets = ip.split('.')
            if len(octets) != 4:
                raise ValueError
            for octet in octets:
                val = int(octet)
                if val < 0 or val > 255:
                    raise ValueError
        except:
            frappe.throw('Invalid CIDR format. Must be in format: x.x.x.x/y') 