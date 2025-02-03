frappe.ui.form.on('Bare Metal Host', {
    refresh: function(frm) {
        // Add button to test API connection
        frm.add_custom_button(__('Test Connection'), function() {
            frappe.call({
                method: 'check_api_connection',
                doc: frm.doc,
                callback: function(r) {
                    frappe.msgprint(__('API connection successful'));
                }
            });
        });

        // Add button to view VMs
        frm.add_custom_button(__('View VMs'), function() {
            frappe.route_options = {
                'bare_metal_host': frm.doc.name
            };
            frappe.set_route('List', 'Virtual Machine');
        });

        // Add button to create VPC
        frm.add_custom_button(__('Create VPC'), function() {
            frappe.new_doc('Bare Metal VPC', {
                'bare_metal_host': frm.doc.name
            });
        });

        // Add maintenance mode button
        if (frm.doc.status === 'Active') {
            frm.add_custom_button(__('Enable Maintenance Mode'), function() {
                frm.set_value('status', 'Maintenance');
                frm.save();
            });
        } else if (frm.doc.status === 'Maintenance') {
            frm.add_custom_button(__('Disable Maintenance Mode'), function() {
                frm.set_value('status', 'Active');
                frm.save();
            });
        }
    },

    validate: function(frm) {
        // Validate API URL format
        if (frm.doc.vm_api_url && !frm.doc.vm_api_url.startsWith('http')) {
            frappe.throw(__('VM API URL must start with http:// or https://'));
        }

        // Validate timeout
        if (frm.doc.vm_api_timeout < 1) {
            frappe.throw(__('API Timeout must be at least 1 second'));
        }
    }
}); 