// Copyright (c) 2024, Frappe and contributors
// For license information, please see license.txt

// The server decides what may move, so the picker offers only what validation accepts
const TRANSFER_QUERIES = 'press.press.doctype.team_change.transfer'

frappe.ui.form.on('Team Change', {
	setup(frm) {
		frm.set_query('document_type', 'resources', () => ({
			query: `${TRANSFER_QUERIES}.transferable_doctypes`,
		}))
		frm.set_query('document_name', 'resources', (doc) => ({
			query: `${TRANSFER_QUERIES}.transferable_resources`,
			filters: { team: doc.from_team },
		}))
	},

	transfer_type(frm) {
		// The balance option is hidden outside a full account transfer, so don't leave it ticked
		if (frm.doc.transfer_type !== 'Full Account' && frm.doc.move_balance)
			frm.set_value('move_balance', 0)
	},

	refresh(frm) {
		// A dashboard request is accepted by the receiving team from the emailed link
		if (frm.is_new() || frm.doc.transfer_completed || frm.doc.document_name)
			return

		if (frm.doc.transfer_type === 'Full Account') {
			frm.add_custom_button(__('Fetch Resources'), () =>
				frm.call('fetch_resources').then(() => frm.reload_doc()),
			)
		}
		frm
			.add_custom_button(__('Transfer'), () => {
				frappe.confirm(
					__('Move the included resources from {0} to {1}?', [
						frm.doc.from_team,
						frm.doc.to_team,
					]),
					() =>
						frm
							.call('transfer')
							.then(() => frm.reload_doc())
							.then(() => frappe.show_alert(__('Transfer complete'))),
				)
			})
			.addClass('btn-primary')
	},
})
