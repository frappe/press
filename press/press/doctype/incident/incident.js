// Copyright (c) 2023, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Incident', {
	refresh(frm) {
		[
			[__('Reboot Database Server'), 'reboot_database_server'],
			[__('Restart Down Benches'), 'restart_down_benches'],
			[__('Cancel Stuck Jobs'), 'cancel_stuck_jobs'],
			[__('Take Grafana screenshots'), 'regather_info_and_screenshots'],
		].forEach(([label, method, condition]) => {
			if (typeof condition === 'undefined' || condition) {
				frm.add_custom_button(
					label,
					() => {
						frappe.confirm(
							`Are you sure you want to ${label.toLowerCase()}?`,
							() => frm.call(method).then((r) => frm.refresh()),
						);
					},
					__('Actions'),
				);
			}
		});

		frm.call('get_down_site').then((r) => {
			if (!r.message) return;
			frm.add_web_link(`https://${r.message}`, __('Visit Down Site'));
		});

		render_stats_image(frm, 'app');
		render_stats_image(frm, 'db');

		// $('.section-head, .section-body').css('max-width', 'none');
	},
	app_server_stats(frm) {
		render_stats_image(frm, 'app');
	},

	db_server_stats(frm) {
		render_stats_image(frm, 'db');
	},
});

function render_stats_image(frm, type) {
	const url = frm.doc[`${type}_server_stats`];
	const wrapper = frm.fields_dict[`${type}_server_stats_html`].$wrapper;

	if (!url) {
		wrapper.html('');
		return;
	}

	const label = type === 'app' ? 'App Server Stats' : 'DB Server Stats';

	wrapper.html(`
        <div style="margin-top: 5px;">
            <label style="font-weight: 600; font-size: 13px; color: var(--text-muted);">
                ${label}
            </label>
        </div>
        <img
            src="${url}"
            alt="${label}"
            style="max-width: 100%; height: auto; border-radius: 6px; border: 1px solid #d1d8dd;"
        />
    `);
}
