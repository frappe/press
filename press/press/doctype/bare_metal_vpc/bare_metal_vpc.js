// Copyright (c) 2025, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Bare Metal VPC', {
    refresh: function(frm) {
        frm.add_custom_button(__('Allocate IP'), function() {
            frappe.call({
                method: 'allocate_ip',
                doc: frm.doc,
                callback: function(r) {
                    if (r.message) {
                        let ips = r.message;
                        frappe.msgprint(
                            `Allocated IPs:<br>
                            Private IP: ${ips.private_ip}<br>
                            Public IP: ${ips.public_ip}<br>
                            Time: ${ips.allocated_at}`
                        );
                        frm.refresh();
                    }
                }
            });
        });

        if (frm.doc.status === 'Active') {
            frm.add_custom_button(__('Delete'), function() {
                frappe.confirm(
                    'Are you sure you want to delete this VPC?',
                    function() {
                        frm.doc.status = 'Deleted';
                        frm.save();
                    }
                );
            });
        }
    },

    validate: function(frm) {
        if (!frm.doc.cidr) {
            frappe.throw(__('CIDR Block is required'));
        }
    }
}); 