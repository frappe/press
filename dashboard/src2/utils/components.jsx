import { h, isVNode, ref } from 'vue';
import { FeatherIcon } from 'frappe-ui';
import ConfirmDialog from '../dialogs/ConfirmDialog.vue';
import DialogWrapper from '../components/DialogWrapper.vue';
import AddressableErrorDialog from '../components/AddressableErrorDialog.vue';

export function icon(name, _class = '') {
	let iconComponent;
	if (typeof name !== 'string' && name?.render) {
		iconComponent = name;
		name = undefined;
	} else {
		iconComponent = FeatherIcon;
	}
	return () => h(iconComponent, { name, class: _class || 'w-4 h-4' });
}

export function confirmDialog({
	title = 'Untitled',
	fields = [],
	message,
	primaryAction,
	onSuccess
}) {
	let dialog = h(ConfirmDialog, {
		title,
		message,
		fields,
		primaryAction,
		onSuccess
	});
	renderDialog(dialog);
	return dialog;
}

export function addressableErrorDialog(name, onDone) {
	renderDialog(
		h(AddressableErrorDialog, {
			name,
			onDone
		})
	);
}

export const dialogs = ref([]);

export function renderDialog(component) {
	if (!isVNode(component)) {
		component = h(component);
	}
	component.id = dialogs.length;
	dialogs.value.push(component);
}

export function renderInDialog(component, options = {}) {
	renderDialog(<DialogWrapper options={options}>{component}</DialogWrapper>);
}
