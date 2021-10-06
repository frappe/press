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
        if(frm.get_field("setup_wizard_complete")) {
            show_site_activation_block(frm);
        } else {
            // TODO: hide site_activation_block
        }

        show_daily_usage_chart(frm);
        show_recent_activity(frm);
	},
	refresh: function (frm) {
		frm.dashboard.set_headline_alert(
			`<div class="container-fluid">
				<div class="row">
					<div class="col-sm-4">CPU Usage: ${frm.doc.current_cpu_usage}%</div>
					<div class="col-sm-4">Database Usage: ${frm.doc.current_database_usage}%</div>
					<div class="col-sm-4">Disk Usage: ${frm.doc.current_disk_usage}%</div>
				</div>
			</div>`
		);
		frm.add_web_link(`https://${frm.doc.name}`, __('Visit Site'));
		frm.add_web_link(
			`/dashboard/sites/${frm.doc.name}`,
			__('Visit Dashboard')
		);

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
	},
});

function show_site_activation_block(frm) {
    var wrapper = frm.get_field("site_activation_block").$wrapper;
    wrapper.empty();
    wrapper.append(`
        <div class="alert alert-info">
            <div class="items-start px-4 md:px-5 py-3.5 text-base rounded-md flex">
                <div class="w-full ml-2">
                    <div class="flex flex-col md:items-baseline md:flex-row">
                        <div>
                            <strong class="mr-2">
                                Site Activation
                            </strong>
                            <span>
                                Please login and complete the setup wizard on your site. Analytics will be collected only after setup is complete.
                            </span>
                            <span class="ml-5">
                                <button class="btn btn-primary">Login</button>
                            </span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `);
}

function show_daily_usage_chart (frm) {
    let site_name = frm.doc.name;
    let local_timezone = moment.tz.guess();

    var wrapper = frm.get_field("daily_usage_block").$wrapper;
    wrapper.empty();

    frappe.call({
        method: "press.api.analytics.daily_usage",
        args: {
            name: site_name,
            timezone: local_timezone
         },
         callback: function(r) {
            let data = r.message.data;
            if(data.length > 0) {
                populate_daily_usage_chart(wrapper, data);
            } else {
                wrapper.append(`
                    <div class="my-3">
                        No data yet
                    </div>
                `)
            }
         }
    });
}

function show_recent_activity(frm) {
    let site_name = frm.doc.name;

    var wrapper = frm.get_field("recent_activity_block").$wrapper;
    wrapper.empty();

    wrapper.append(`
        <span>
            History of recent activities performed on your site
        </span>
    `)

    frappe.call({
        method: "press.api.site.overview",
        args: {
            name: site_name
         },
         callback: function(r) {
            let recent_activity = r.message.recent_activity;
            populate_recent_activity_list(wrapper, recent_activity);
         }
    });
}

function populate_daily_usage_chart(wrapper, data) {
    // TODO: make a chart
    for (let i = 0; i < data.length; i++) {
        wrapper.append(`<li> data: ` + data[i].date + ' max: '+ data[i].max + `</li>`);
    }
}

function populate_recent_activity_list(wrapper, recent_activity) {
    for(let i = 0; i < recent_activity.length; i++) {
        wrapper.append(`
            <li> ` + recent_activity[i].action +
            " by " + recent_activity[i].owner +
            " | " + recent_activity[i].creation +
            ` </li>
        `);
    }
}