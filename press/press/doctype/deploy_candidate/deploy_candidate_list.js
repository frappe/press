frappe.listview_settings['Deploy Candidate'] = {
	refresh: show_toggle_builds_button,
};

function show_toggle_builds_button(list_view) {
	if (!has_common(frappe.user_roles, ['Administrator', 'System Manager']))
		return;

	frappe.db
		.get_single_value('Press Settings', 'suspend_builds')
		.then((suspend_builds) => {
			const label = suspend_builds ? __('Resume Builds') : __('Suspend Builds');

			list_view.page.add_inner_button(label, () => {
				frappe
					.xcall(
						'press.press.doctype.deploy_candidate.deploy_candidate.toggle_builds',
						{ suspend: !suspend_builds },
					)
					.then(() => {
						// clear the button and show one with the opposite label
						list_view.page.remove_inner_button(label);
						show_toggle_builds_button(list_view);
					});
			});
		});
}
