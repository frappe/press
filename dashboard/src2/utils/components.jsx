import { FeatherIcon } from 'frappe-ui';
import { h, isVNode, ref, defineAsyncComponent } from 'vue';
import AddressableErrorDialog from '../components/AddressableErrorDialog.vue';
import DialogWrapper from '../components/DialogWrapper.vue';
import ConfirmDialog from '../dialogs/ConfirmDialog.vue';

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

/**
 * 
 * @param {import('../objects/common/types').DialogConfig} param0 
 * @returns 
 */
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

export function cardBrandIcon(brand) {
	const component = {
		'master-card': defineAsyncComponent(() =>
			import('@/components/icons/cards/MasterCard.vue')
		),
		visa: defineAsyncComponent(() =>
			import('@/components/icons/cards/Visa.vue')
		),
		amex: defineAsyncComponent(() =>
			import('@/components/icons/cards/Amex.vue')
		),
		jcb: defineAsyncComponent(() =>
			import('@/components/icons/cards/JCB.vue')
		),
		generic: defineAsyncComponent(() =>
			import('@/components/icons/cards/Generic.vue')
		),
		'union-pay': defineAsyncComponent(() =>
			import('@/components/icons/cards/UnionPay.vue')
		)
	}[brand || 'generic'];

	return h(component, { class: 'h-4 w-6' });
}