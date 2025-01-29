// Copyright (c) 2025, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on("SSH Access Audit", {
    refresh(frm) {
        [
            [__('Run'), 'run', frm.doc.status === 'Pending'],
        ].forEach(([label, method, condition]) => {
            if (condition) {
                frm.add_custom_button(
                    label,
                    () => {
                        frappe.confirm(
                            `Are you sure you want to ${label.toLowerCase()}?`,
                            () => frm.call(method).then(() => frm.refresh()),
                        );
                    },
                    __('Actions'),
                );
            }
        });
    },
});
