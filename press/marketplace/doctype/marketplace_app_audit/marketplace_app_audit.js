// Copyright (c) 2026, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Marketplace App Audit', {
	refresh(frm) {
		inject_audit_check_styles();
		paint_audit_check_rows(frm);

		frm.add_custom_button(__('Re-run Audit'), async () => {
			if (['Queued', 'Running'].includes(frm.doc.status)) {
				frappe.msgprint(__('Audit is already in progress.'));
				return;
			}

			await frm.call('rerun_audit', { doc: frm.doc });
			frappe.show_alert({ message: __('Audit re-queued'), indicator: 'blue' });
			frm.reload_doc();
		});
	},
});

$(document).on('grid-row-render', (e, grid_row) => {
	if (grid_row.frm?.doctype !== 'Marketplace App Audit') return;
	if (grid_row.grid?.df?.fieldname !== 'audit_checks') return;
	paint_audit_check_rows(grid_row.frm);
});

const RESULT_CLASS = {
	Pass: 'audit-check--pass',
	'Needs Improvement': 'audit-check--needs-improvement',
	Warn: 'audit-check--warn',
	Fail: 'audit-check--fail',
	Skipped: 'audit-check--skipped',
	Error: 'audit-check--error',
};

function paint_audit_check_rows(frm) {
	const grid = frm.fields_dict.audit_checks?.grid;
	if (!grid) return;

	const all_classes = Object.values(RESULT_CLASS).join(' ');
	grid.grid_rows.forEach((row) => {
		const $row = $(row.row).closest('.grid-row');
		$row.removeClass(all_classes);

		const cls = RESULT_CLASS[row.doc.result];
		if (cls) $row.addClass(cls);
	});
}

function inject_audit_check_styles() {
	if (document.getElementById('marketplace-audit-check-styles')) return;

	$(`<style id="marketplace-audit-check-styles">
		.audit-check--pass .grid-static-col,
		.audit-check--pass .data-row { background: var(--green-50); }

		.audit-check--needs-improvement .grid-static-col,
		.audit-check--needs-improvement .data-row { background: var(--blue-50); }

		.audit-check--warn .grid-static-col,
		.audit-check--warn .data-row { background: var(--yellow-50); }

		.audit-check--fail .grid-static-col,
		.audit-check--fail .data-row,
		.audit-check--error .grid-static-col,
		.audit-check--error .data-row { background: var(--red-50); }

		.audit-check--skipped .grid-static-col,
		.audit-check--skipped .data-row { background: var(--gray-50); }
	</style>`).appendTo(document.head);
}
