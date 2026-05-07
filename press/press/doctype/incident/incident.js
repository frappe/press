// Copyright (c) 2023, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Incident', {
	setup(frm) {
		$(frm.wrapper).on('grid-row-render', function (e, grid_row) {
			if (grid_row.grid.df.fieldname !== 'down_benches') return;
			render_down_bench_row(grid_row);
		});
	},
	refresh(frm) {
		render_server_status(frm);
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
	},
	app_server_stats(frm) {
		render_stats_image(frm, 'app');
	},

	db_server_stats(frm) {
		render_stats_image(frm, 'db');
	},
});

function render_down_bench_row(grid_row) {
	let value = grid_row.doc && grid_row.doc.last_seen_seconds_ago;
	let $col = grid_row.columns && grid_row.columns['last_seen_seconds_ago'];
	if (!$col) return;

	let $cell = $col.static_area;
	if (!$cell || !$cell.length) return;

	if (value == -1) {
		$cell.html(`<span style="color:red;font-weight:bold;">Down</span>`);
	} else if (value != null && value !== '') {
		let seconds = parseInt(value, 10);
		let mins = Math.floor(seconds / 60);
		let secs = seconds % 60;
		let display = `${mins}:${String(secs).padStart(2, '0')}`;

		let color = 'green';
		if (seconds > 60 && seconds <= 600) {
			color = 'orange';
		} else if (seconds > 600) {
			color = 'red';
		}

		$cell.html(
			`<span style="color:${color};font-weight:bold;">${display}</span>`,
		);
	}
}

function render_server_status(frm) {
	const UNHEALTHY_SERVER = ['Unreachable'];
	const UNHEALTHY_DB = ['Unreachable', 'Reachable - DB Unhealthy'];

	for (const [fieldname, unhealthyValues] of [
		['server_status', UNHEALTHY_SERVER],
		['db_server_status', UNHEALTHY_DB],
	]) {
		const value = frm.doc[fieldname];
		const $field = frm.fields_dict[fieldname];
		if (!$field) continue;

		const isUnhealthy = unhealthyValues.includes(value);
		$field.$wrapper
			.find('.control-value, .like-disabled-input')
			.css('color', isUnhealthy ? 'red' : '');
	}
}

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
