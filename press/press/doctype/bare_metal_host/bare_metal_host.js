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
        }, __("Actions"));

        // Add button to view VMs
        frm.add_custom_button(__('View VMs'), function() {
            frappe.route_options = {
                'bare_metal_host': frm.doc.name
            };
            frappe.set_route('List', 'Virtual Machine');
        }, __("Actions"));

        // Add button to create VPC
        frm.add_custom_button(__('Create VPC'), function() {
            frappe.new_doc('Bare Metal VPC', {
                'bare_metal_host': frm.doc.name
            });
        }, __("Actions"));

        // Add maintenance mode button
        if (frm.doc.status === 'Active') {
            frm.add_custom_button(__('Enable Maintenance Mode'), function() {
                frm.set_value('status', 'Maintenance');
                frm.save();
            }, __("Actions"));
        } else if (frm.doc.status === 'Maintenance') {
            frm.add_custom_button(__('Disable Maintenance Mode'), function() {
                frm.set_value('status', 'Active');
                frm.save();
            }, __("Actions"));
        }

        // Add button to test cloud-init templates
        if (frm.doc.allow_custom_cloud_init) {
            frm.add_custom_button(__('Test Cloud-Init Templates'), function() {
                let d = new frappe.ui.Dialog({
                    title: __('Test Cloud-Init Templates'),
                    fields: [
                        {
                            label: __('VM Name'),
                            fieldname: 'vm_name',
                            fieldtype: 'Data',
                            reqd: 1
                        },
                        {
                            label: __('IP Address'),
                            fieldname: 'ip_address',
                            fieldtype: 'Data',
                            reqd: 1
                        },
                        {
                            label: __('Gateway'),
                            fieldname: 'gateway',
                            fieldtype: 'Data',
                            reqd: 1
                        },
                        {
                            label: __('Custom Configuration'),
                            fieldname: 'custom_config',
                            fieldtype: 'Code',
                            options: 'JSON'
                        },
                        {
                            fieldtype: 'Section Break',
                            label: __('Generated Configuration')
                        },
                        {
                            label: __('User Data'),
                            fieldname: 'user_data',
                            fieldtype: 'Code',
                            options: 'YAML',
                            read_only: 1
                        },
                        {
                            label: __('Meta Data'),
                            fieldname: 'meta_data',
                            fieldtype: 'Code',
                            options: 'YAML',
                            read_only: 1
                        },
                        {
                            label: __('Network Config'),
                            fieldname: 'network_config',
                            fieldtype: 'Code',
                            options: 'YAML',
                            read_only: 1
                        }
                    ],
                    primary_action_label: __('Generate'),
                    primary_action(values) {
                        frappe.call({
                            method: 'get_cloud_init_config',
                            doc: frm.doc,
                            args: {
                                vm_name: values.vm_name,
                                network_config: {
                                    ip_address: values.ip_address,
                                    gateway: values.gateway
                                },
                                custom_config: values.custom_config ? JSON.parse(values.custom_config) : null
                            },
                            callback: function(r) {
                                if (r.message) {
                                    d.set_value('user_data', r.message.user_data);
                                    d.set_value('meta_data', r.message.meta_data);
                                    d.set_value('network_config', r.message.network_config);
                                }
                            }
                        });
                    }
                });
                d.show();
            }, __("Cloud Init"));
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

        // Validate cloud-init templates
        if (frm.doc.allow_custom_cloud_init) {
            try {
                if (frm.doc.custom_user_data_template) {
                    // Basic Jinja2 syntax check
                    if (frm.doc.custom_user_data_template.includes('{{') && 
                        !frm.doc.custom_user_data_template.includes('}}')) {
                        frappe.throw(__('Invalid Jinja2 syntax in Custom User Data Template'));
                    }
                }
                if (frm.doc.custom_meta_data_template) {
                    if (frm.doc.custom_meta_data_template.includes('{{') && 
                        !frm.doc.custom_meta_data_template.includes('}}')) {
                        frappe.throw(__('Invalid Jinja2 syntax in Custom Meta Data Template'));
                    }
                }
                if (frm.doc.custom_network_config_template) {
                    if (frm.doc.custom_network_config_template.includes('{{') && 
                        !frm.doc.custom_network_config_template.includes('}}')) {
                        frappe.throw(__('Invalid Jinja2 syntax in Custom Network Config Template'));
                    }
                }
            } catch (e) {
                frappe.throw(__('Error validating cloud-init templates: ' + e.message));
            }
        }
    },

    allow_custom_cloud_init: function(frm) {
        // Clear custom templates when disabling custom cloud-init
        if (!frm.doc.allow_custom_cloud_init) {
            frm.set_value('custom_user_data_template', '');
            frm.set_value('custom_meta_data_template', '');
            frm.set_value('custom_network_config_template', '');
        }
        frm.trigger('refresh');
    }
}); 