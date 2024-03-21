// Copyright (c) 2024, Frappe and contributors
// For license information, please see license.txt

// Most of the code here imitates the code from
// frappe/desk/doctype/system_console/system_console.js
frappe.ui.form.on('Bench Shell', {
	onload(frm) {
		frappe.ui.keys.add_shortcut({
			shortcut: 'shift+enter',
			action: () => frm.page.btn_primary.trigger('click'),
			page: frm.page,
			description: __('Run Bench Shell command'),
			ignore_inputs: true,
		});
	},

	refresh(frm) {
		frm.disable_save();
		frm.page.set_primary_action(__('Run'), async ($btn) => {
			$btn.text(__('Running Command...'));
			return frm.execute_action('Run').finally(() => $btn.text(__('Run')));
		});

		const bench = localStorage.getItem('bench_shell_bench');
		const command = localStorage.getItem('bench_shell_command');

		if (!bench || !command) {
			return;
		}

		frm.set_value('bench', bench);
		frm.set_value('command', command);

		['output', 'traceback', 'directory'].forEach((f) => frm.set_value(f, null));
		['returncode', 'duration'].forEach((f) => frm.set_value(f, 0));

		localStorage.removeItem('bench_shell_bench');
		localStorage.removeItem('bench_shell_command');
	},
});
