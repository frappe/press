// Copyright (c) 2019, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Site', {
	onload: function (frm) {
		frm.set_query('bench', function () {
			return {
				filters: {
					server: frm.doc.server,
					status: 'Active',
				},
			};
		});
		frm.set_query('host_name', () => {
			return {
				filters: {
					site: frm.doc.name,
					status: 'Active'
				},
			};
		});
	},
	refresh: async function (frm) {
		// frm.dashboard.set_headline_alert(
		// 	`<div class="container-fluid">
		// 		<div class="row">
		// 			<div class="col-sm-4">CPU Usage: ${frm.doc.current_cpu_usage}%</div>
		// 			<div class="col-sm-4">Database Usage: ${frm.doc.current_database_usage}%</div>
		// 			<div class="col-sm-4">Disk Usage: ${frm.doc.current_disk_usage}%</div>
		// 		</div>
		// 	</div>`
		// );
        let site = frm.get_doc();
        let account = await frappe.call({
            method: 'press.api.account.get'
        }).then(resp => resp.message);

        frm.add_custom_button(__('Visit Site'), () => {
            window.open(`https://${frm.doc.name}`);
        });
        frm.add_custom_button(__('Goto Dashboard'), () => {
            window.location.href = `/dashboard/sites/${frm.docname}/overview`;
        });
        if (site.status === 'Active') {
            frm.add_custom_button(__('Login as Adminstrator'), () => {
                if(account) {
                    if (site.team === account.team.name) {
                        login_as_admin(site.name);
                    } else {
                        new frappe.ui.Dialog({
                            title: 'Login as Adminstrator',
                            fields: [
                                {
                                    label: 'Please enter reason for this login.',
                                    fieldname: 'reason',
                                    fieldtype: 'Small Text'
                                }
                            ],
                            primary_action_label: 'Login',
                            primary_action(values) {
                                if (values) {
                                    let reason = values.reason;
                                    console.log(reason);
                                    login_as_admin(site.name, reason);
                                } else {
                                    frappe.throw(__('Reason field should not be empty'))
                                }
                                this.hide();
                            }
                        }).show();                    
                    }
                } else {
                    frappe.throw(__("could'nt retrieve account. Check Error Log for more information"));
                }
            });
        }
        frm.add_custom_button(__('Visit Site'), () => {
            window.location.href = `https://${frm.doc.name}`;
        });

		[
			[__('Backup'), 'backup'],
		].forEach(([label, method]) => {
			frm.add_custom_button(
				label,
				() => { frm.call(method).then((r) => frm.refresh()) },
				__('Actions')
			);
		});
		[
			[__('Archive'), 'archive'],
			[__('Cleanup after Archive'), 'cleanup_after_archive'],
			[__('Migrate'), 'migrate'],
			[__('Reinstall'), 'reinstall'],
			[__('Restore'), 'restore_site'],
			[__('Restore Tables'), 'restore_tables'],
			[__('Clear Cache'), 'clear_cache'],
			[__('Update'), 'schedule_update'],
			[__('Deactivate'), 'deactivate'],
			[__('Activate'), 'activate'],
		].forEach(([label, method]) => {
			frm.add_custom_button(
				label,
				() => {
					frappe.confirm(
						`Are you sure you want to ${label.toLowerCase()} this site?`,
						() => frm.call(method).then((r) => frm.refresh())
					);
				},
				__('Actions')
			);
		});
		[
			[__('Suspend'), 'suspend'],
			[__('Unsuspend'), 'unsuspend'],
		].forEach(([label, method]) => {
			frm.add_custom_button(
				label,
				() => {
					frappe.prompt(
						{ fieldtype: 'Data', label: 'Reason', fieldname: 'reason', reqd: 1 },
						({ reason }) => {
							frm.call(method, { reason }).then((r) => frm.refresh());
						},
						__('Provide Reason')
					);
				},
				__('Actions')
			);
		});
		frm.toggle_enable(['host_name'], frm.doc.status === 'Active');
    }
});

function login_as_admin(site_name, reason=null) {
    frappe.call({
        method: 'press.api.site.login',
        args: {
            name: site_name,
            reason: reason
        }
    }).then((sid) => {
        if (sid) {
            window.open(`https://${site_name}/desk?sid=${sid}`, '_blank');
        }
    }, (error) => {
        console.log(error);
        frappe.throw(__(`An error occurred!!`));
    })
}
