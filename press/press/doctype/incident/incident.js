// Copyright (c) 2023, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Incident', {
	refresh(frm) {
		[
			[
				__('Check if Resolved'),
				'check_if_resolved',
				frm.doc.status !== 'Resolved',
			],
			[__('Reboot Database Server'), 'reboot_database_server'],
			[__('Restart Down Benches'), 'restart_down_benches'],
			[__('Cancel Stuck Jobs'), 'cancel_stuck_jobs'],
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

		frm.dashboard.clear_headline();
		frm.dashboard.set_headline(
			`<div class="flex justify-between">${frm.doc.no_of_down_sites} Sites Down</div>`,
			frm.doc.no_of_down_sites > 0 ? 'red' : 'green',
		);

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
