// Copyright (c) 2023, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Incident', {
	refresh(frm) {
		;[
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
						)
					},
					__('Actions'),
				)
			}
		})
		if (!frm.doc.ignored) {
			frm.add_custom_button(__('Ignore Incident'), () => {
				frappe.prompt(
					{
						fieldname: 'reason',
						fieldtype: 'Small Text',
						label: __('Reason'),
						description: __(
							'Only stops phone calls to the Frappe Cloud team. Nothing changes for customers: they still see this incident and get its emails and calls.',
						),
						reqd: 1,
					},
					({ reason }) =>
						frm.call('ignore', { reason }).then(() => frm.reload_doc()),
					__('Why ignore this incident?'),
					__('Ignore'),
				)
			})
		} else {
			frm.add_custom_button(__('Stop Ignoring'), () => {
				frappe.prompt(
					{
						fieldname: 'reason',
						fieldtype: 'Small Text',
						label: __('Reason'),
						description: __(
							'Phone calls to the Frappe Cloud team resume for this incident.',
						),
						reqd: 1,
					},
					({ reason }) =>
						frm.call('stop_ignoring', { reason }).then(() => frm.reload_doc()),
					__('Why stop ignoring this incident?'),
					__('Stop Ignoring'),
				)
			})
		}
		frm.add_custom_button(__('Send Email'), () => {
			frm.call('get_email_subject').then(({ message: subject }) => {
				const dialog = new frappe.ui.Dialog({
					title: __('Email Customer'),
					fields: [
						{
							fieldname: 'subject',
							fieldtype: 'Data',
							label: __('Subject'),
							default: subject,
							reqd: 1,
						},
						{
							fieldname: 'message',
							fieldtype: 'Text Editor',
							label: __('Message'),
							reqd: 1,
						},
					],
					primary_action_label: __('Send'),
					primary_action: ({ subject, message }) =>
						frm.call('send_custom_email', { subject, message }).then(() => {
							dialog.hide()
							frappe.show_alert({
								message: __('Email sent'),
								indicator: 'green',
							})
							frm.reload_doc()
						}),
				})
				dialog.show()
			})
		})
		frm.call('get_down_site').then((r) => {
			if (!r.message) return
			frm.add_web_link(`https://${r.message}`, __('Visit Down Site'))
		})
	},
})
