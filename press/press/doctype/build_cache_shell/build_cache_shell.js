// Copyright (c) 2024, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Build Cache Shell', {
	onload(frm) {
		frappe.ui.keys.add_shortcut({
			shortcut: 'shift+enter',
			action: () => frm.page.btn_primary.trigger('click'),
			page: frm.page,
			description: __('Run Build Cache Shell command'),
			ignore_inputs: true,
		});
	},

	refresh(frm) {
		frm.disable_save();
		frm.page.set_primary_action(__('Run'), async ($btn) => {
			$btn.text(__('Running Command...'));
			return frm.execute_action('Run').finally(() => $btn.text(__('Run')));
		});

		const command = localStorage.getItem('build_cache_shell_command');
		if (!command) {
			return;
		}

		frm.set_value('bench', bench);
		frm.set_value('command', command);

		['output', 'cwd', 'image_tag'].forEach((f) => frm.set_value(f, null));
		frm.set_value('returncode', 0);

		localStorage.removeItem('build_cache_shell_command');
	},
});
