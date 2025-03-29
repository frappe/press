// Copyright (c) 2021, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Cluster', {
	refresh: function (frm) {
		[
			[__('Create Servers'), 'create_servers', frm.doc.status === 'Active'],
			[__('Add Images'), 'add_images', frm.doc.status === 'Active'],
		].forEach(([label, method, condition]) => {
			if (typeof condition === 'undefined' || condition) {
				frm.add_custom_button(
					label,
					() => {
						frm.call(method).then((r) => frm.refresh());
					},
					__('Actions'),
				);
			}
		});
		if (frm.doc.vpc_id) {
			if (frm.doc.cloud_provider === 'AWS EC2') {
				frm.add_web_link(
					`https://${frm.doc.region}.console.aws.amazon.com/vpc/home?region=${frm.doc.region}#VpcDetails:VpcId=${frm.doc.vpc_id}`,
					__('Visit AWS Dashboard'),
				);
			} else if (frm.doc.cloud_provider === 'OCI') {
				frm.add_web_link(
					`https://cloud.oracle.com/networking/vcns/${frm.doc.vpc_id}?region=${frm.doc.region}`,
					__('Visit OCI Dashboard'),
				);
			}
		}
		
		// Add a link to the Bare Metal Host if selected
		if (frm.doc.cloud_provider === 'Bare Metal Host' && frm.doc.bare_metal_host) {
			frm.add_web_link(
				`/app/bare-metal-host/${frm.doc.bare_metal_host}`,
				__('View Bare Metal Host'),
			);
		}
	},
	
	cloud_provider: function(frm) {
		// Show/hide fields based on cloud provider
		frm.toggle_display('bare_metal_section', frm.doc.cloud_provider === 'Bare Metal Host');
		frm.toggle_display('aws_section', frm.doc.cloud_provider === 'AWS EC2');
		frm.toggle_display('oci_section', frm.doc.cloud_provider === 'OCI');
		
		// Set required fields based on provider
		if (frm.doc.cloud_provider === 'Bare Metal Host') {
			frm.set_df_property('bare_metal_host', 'reqd', 1);
		} else {
			frm.set_df_property('bare_metal_host', 'reqd', 0);
		}
	},
	
	// Filter bare metal hosts to only show VM-capable hosts
	bare_metal_host: function(frm) {
		frm.set_query("bare_metal_host", function() {
			return {
				filters: {
					"is_vm_host": 1,
					"status": "Active"
				}
			};
		});
	}
});
