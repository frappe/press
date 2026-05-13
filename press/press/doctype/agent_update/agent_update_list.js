// Copyright (c) 2025, Frappe and contributors
// For license information, please see license.txt

frappe.listview_settings['Agent Update'] = {
	onload(listview) {
		add_bulk_action(listview, __('Start Selected'), 'execute');
		add_bulk_action(listview, __('Pause Selected'), 'pause');
		add_bulk_action(listview, __('Force Continue Selected'), 'force_continue');
	},
};

function add_bulk_action(listview, label, method) {
	listview.page.add_action_item(label, () => {
		const selected = listview.get_checked_items();

		if (!selected.length) {
			frappe.msgprint(__('Please select at least one record.'));
			return;
		}

		frappe.confirm(
			__('Run {0} on {1} record(s)?', [label, selected.length]),
			async () => {
				frappe.dom.freeze(__('Processing…'));

				const success = [];
				const failed = [];

				for (const row of selected) {
					console.log(row);

					try {
						const res = await fetch('/api/method/run_doc_method', {
							method: 'POST',
							headers: {
								'Content-Type': 'application/json',
								'X-Frappe-CSRF-Token': frappe.csrf_token,
							},
							body: JSON.stringify({
								docs: JSON.stringify({
									doctype: 'Agent Update',
									name: row.name,
									modified: row.modified,
								}),
								method: method,
							}),
						});

						if (!res.ok) {
							const data = await res.json();
							throw new Error(data?.exception || __('Server Error'));
						}

						success.push(row.name);
					} catch (e) {
						failed.push(`${row.name}: ${e.message}`);
					}
				}

				frappe.dom.unfreeze();
				show_summary(label, success, failed);
				listview.refresh();
			},
		);
	});
}

function show_summary(label, success, failed) {
	const lines = [];

	if (success.length) {
		lines.push(__('Succeeded:'));
		success.forEach((name) => lines.push(`- <a>${name}</`));
	}

	if (failed.length) {
		if (lines.length) lines.push('');
		lines.push(__('Failed:'));
		failed.forEach((row) => lines.push(`- ${row}`));
	}

	frappe.msgprint({
		title: __('Summary', [label]),
		message: lines.join('<br>'),
		indicator: failed.length ? 'orange' : 'green',
	});
}
