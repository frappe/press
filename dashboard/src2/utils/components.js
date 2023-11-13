import { h, ref } from 'vue';
import { FeatherIcon } from 'frappe-ui';
import ConfirmDialog from '../dialogs/ConfirmDialog.vue';

export function icon(name, _class = '') {
	return () => h(FeatherIcon, { name, class: _class || 'w-4 h-4' });
}

export function confirmDialog({ title = 'Untitled', fields = [], onSuccess }) {
	renderDialog(
		h(ConfirmDialog, {
			title,
			fields,
			onSuccess
		})
	);
}

export const dialogs = ref([]);

export function renderDialog(component) {
	component.id = dialogs.length;
	dialogs.value.push(component);
}
