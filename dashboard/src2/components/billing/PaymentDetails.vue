<template>
	<div class="flex flex-col gap-4">
		<div class="text-lg font-semibold text-gray-900">Payment details</div>
		<div class="flex flex-col">
			<div
				v-if="team.doc.payment_mode == 'Card'"
				class="flex items-center justify-between text-base text-gray-900"
			>
				<div class="flex flex-col gap-1.5">
					<div class="font-medium">Active Card</div>
					<div class="overflow-hidden text-ellipsis text-gray-700">
						<div
							v-if="team.doc.payment_method"
							class="inline-flex items-center gap-2"
						>
							<component :is="cardBrandIcon(team.doc.payment_method.brand)" />
							<div class="text-gray-700">
								<span>{{ team.doc.payment_method.name_on_card }}</span>
								<span> &middot; Card ending in •••• </span>
								<span>{{ team.doc.payment_method.last_4 }}</span>
							</div>
						</div>
						<span v-else class="text-gray-700">No card added</span>
					</div>
				</div>
				<div class="shrink-0">
					<Button
						:label="team.doc.payment_method ? 'Change card' : 'Add card'"
						@click="changeMethod"
					>
						<template v-if="!team.doc.payment_method" #prefix>
							<FeatherIcon class="h-4" name="plus" />
						</template>
					</Button>
				</div>
			</div>
			<div
				v-if="team.doc.payment_mode == 'Card'"
				class="my-3 h-px bg-gray-100"
			/>
			<div class="flex items-center justify-between text-base text-gray-900">
				<div class="flex flex-col gap-1.5">
					<div class="font-medium">Mode of payment</div>
					<div
						v-if="team.doc.payment_mode"
						class="inline-flex items-center gap-2 text-gray-700"
					>
						<FeatherIcon class="h-4" name="info" />
						{{ paymentMode.description }}
					</div>
					<span v-else class="text-gray-700">Not set</span>
				</div>
				<div class="shrink-0">
					<Dropdown :options="paymentModeOptions">
						<template #default="{ open }">
							<Button
								:label="team.doc.payment_mode ? paymentMode.label : 'Set mode'"
							>
								<template #suffix>
									<FeatherIcon
										:name="open ? 'chevron-up' : 'chevron-down'"
										class="h-4"
									/>
								</template>
							</Button>
						</template>
					</Dropdown>
				</div>
			</div>
			<div class="my-3 h-px bg-gray-100" />
			<div class="flex items-center justify-between text-base text-gray-900">
				<div class="flex flex-col gap-1.5">
					<div class="font-medium">Credit balance</div>
					<div class="text-gray-700">
						{{ availableCredits || currency + ' 0.00' }}
					</div>
				</div>
				<div class="shrink-0">
					<Button
						:label="'Add credit'"
						@click="
							() => {
								showMessage = false;
								if (!billingDetailsSummary) {
									showMessage = true;
									showBillingDetailsDialog = true;
									return;
								}
								showAddPrepaidCreditsDialog = true;
							}
						"
					>
						<template #prefix>
							<FeatherIcon class="h-4" name="plus" />
						</template>
					</Button>
				</div>
			</div>
			<div class="my-3 h-px bg-gray-100" />
			<div class="flex items-center justify-between text-base text-gray-900">
				<div class="flex flex-col gap-1.5">
					<div class="font-medium">Billing address</div>
					<div v-if="billingDetailsSummary" class="leading-5 text-gray-700">
						{{ billingDetailsSummary }}
					</div>
					<div v-else class="text-gray-700">No address</div>
				</div>
				<div class="shrink-0">
					<Button
						:label="billingDetailsSummary ? 'Edit ' : 'Add billing address'"
						@click="
							() => {
								showMessage = false;
								showBillingDetailsDialog = true;
							}
						"
					>
						<template v-if="!billingDetailsSummary" #prefix>
							<FeatherIcon class="h-4" name="plus" />
						</template>
					</Button>
				</div>
			</div>
		</div>
	</div>
	<BillingDetailsDialog
		v-if="showBillingDetailsDialog"
		v-model="showBillingDetailsDialog"
		:showMessage="showMessage"
		@success="billingDetails.reload()"
	/>
	<AddPrepaidCreditsDialog
		v-if="showAddPrepaidCreditsDialog"
		v-model="showAddPrepaidCreditsDialog"
		:showMessage="showMessage"
		@success="upcomingInvoice.reload()"
	/>
	<AddCardDialog
		v-if="showAddCardDialog"
		v-model="showAddCardDialog"
		:showMessage="showMessage"
		@success="
			() => {
				showMessage = false;
				showAddCardDialog = false;
				team.reload();
			}
		"
	/>
	<ChangeCardDialog
		v-if="showChangeCardDialog"
		v-model="showChangeCardDialog"
		@addCard="
			() => {
				showChangeCardDialog = false;
				showAddCardDialog = true;
			}
		"
		@success="() => team.reload()"
	/>
</template>
<script setup>
import DropdownItem from './DropdownItem.vue';
import BillingDetailsDialog from './BillingDetailsDialog.vue';
import AddPrepaidCreditsDialog from './AddPrepaidCreditsDialog.vue';
import AddCardDialog from './AddCardDialog.vue';
import ChangeCardDialog from './ChangeCardDialog.vue';
import { Dropdown, Button, FeatherIcon, createResource } from 'frappe-ui';
import {
	cardBrandIcon,
	confirmDialog,
	renderDialog,
} from '../../utils/components';
import { computed, ref, inject, h, defineAsyncComponent } from 'vue';
import router from '../../router';

const team = inject('team');
const {
	availableCredits,
	upcomingInvoice,
	currentBillingAmount,
	unpaidInvoices,
} = inject('billing');

const showBillingDetailsDialog = ref(false);
const showAddPrepaidCreditsDialog = ref(false);
const showAddCardDialog = ref(false);
const showChangeCardDialog = ref(false);

const currency = computed(() => (team.doc.currency == 'INR' ? '₹' : '$'));

const billingDetails = createResource({
	url: 'press.api.account.get_billing_information',
	cache: 'billingDetails',
	auto: true,
});

const changePaymentMode = createResource({
	url: 'press.api.billing.change_payment_mode',
	onSuccess: () => setTimeout(() => team.reload(), 1000),
});

const billingDetailsSummary = computed(() => {
	let _billingDetails = billingDetails.data;
	if (!_billingDetails) return '';

	const { billing_name, address_line1, city, state, country, pincode, gstin } =
		_billingDetails || {};
	return [
		billing_name,
		address_line1,
		city,
		state,
		country,
		pincode,
		gstin == 'Not Applicable' ? '' : gstin,
	]
		.filter(Boolean)
		.join(', ');
});

const paymentModeOptions = [
	{
		label: 'Card',
		value: 'Card',
		description: 'Your card will be charged for monthly subscription',
		component: () =>
			h(DropdownItem, {
				label: 'Card',
				active: team.doc.payment_mode === 'Card',
				onClick: () => updatePaymentMode('Card'),
			}),
	},
	{
		label: 'Prepaid credits',
		value: 'Prepaid Credits',
		description:
			'You will be charged from your credit balance for monthly subscription',
		component: () =>
			h(DropdownItem, {
				label: 'Prepaid credits',
				active: team.doc.payment_mode === 'Prepaid Credits',
				onClick: () => updatePaymentMode('Prepaid Credits'),
			}),
	},
	{
		label: 'Paid by Partner',
		value: 'Paid By Partner',
		condition: () => team.doc.partner_email,
		description: 'Your partner will be charged for monthly subscription',
		component: () =>
			h(DropdownItem, {
				label: 'Paid by Partner',
				active: team.doc.payment_mode === 'Paid by Partner',
				onClick: () =>
					confirmDialog({
						title: 'Confirm Payment Mode',
						message: `By changing the payment mode to <strong>Paid by Partner</strong>, following details will be shared with your partner: <br><br><li>Site/Server name</li> <li>Plan name</li><li>Number of days site/server is active</li><br>Are you sure you want to proceed?`,
						primaryAction: {
							label: 'Change Payment Mode',
							variant: 'solid',
							onClick: ({ hide }) => {
								updatePaymentMode('Paid By Partner');
								hide();
							},
						},
					}),
			}),
	},
	{
		component: () =>
			h('div', [
				h('div', { class: 'border-t border-gray-200 my-1' }),
				h(DropdownItem, null, {
					default: () =>
						h('div', { class: 'flex gap-2' }, [
							h(
								'a',
								{
									href: 'https://frappecloud.com/payment-options',
									target: '_blank',
								},
								'Alternate Payment Methods',
							),
							h(FeatherIcon, { name: 'external-link', class: 'h-4' }),
						]),
				}),
			]),
	},
];

const paymentMode = computed(() => {
	return paymentModeOptions.find((o) => o.value === team.doc.payment_mode);
});

function payUnpaidInvoices() {
	let _unpaidInvoices = unpaidInvoices.data;
	if (_unpaidInvoices.length > 1) {
		if (team.doc.payment_mode === 'Prepaid Credits') {
			showAddPrepaidCreditsDialog.value = true;
		} else {
			confirmDialog({
				title: 'Multiple unpaid invoices',
				message:
					'You have multiple unpaid invoices. Please pay them from the invoices page',
				primaryAction: {
					label: 'Go to invoices',
					variant: 'solid',
					onClick: ({ hide }) => {
						router.push({ name: 'BillingInvoices' });
						hide();
					},
				},
			});
		}
	} else {
		let invoice = _unpaidInvoices[0];
		if (invoice.stripe_invoice_url && team.doc.payment_mode === 'Card') {
			window.open(
				`/api/method/press.api.client.run_doc_method?dt=Invoice&dn=${invoice.name}&method=stripe_payment_url`,
			);
		} else {
			showAddPrepaidCreditsDialog.value = true;
		}
	}
}

const showMessage = ref(false);
function updatePaymentMode(mode) {
	showMessage.value = false;
	if (!billingDetailsSummary.value) {
		showMessage.value = true;
		showBillingDetailsDialog.value = true;
		return;
	}
	if (mode === 'Prepaid Credits' && team.doc.balance === 0) {
		showMessage.value = true;
		showAddPrepaidCreditsDialog.value = true;
		return;
	} else if (mode === 'Card' && !team.doc.payment_method) {
		showMessage.value = true;
		showAddCardDialog.value = true;
	} else if (mode === 'Paid By Partner' && Boolean(unpaidInvoices.data.length > 0)) {
		if (unpaidInvoices.data) {
			payUnpaidInvoices();
			return;
		}
		if (currentBillingAmount.value) {
			const finalizeInvoicesDialog = defineAsyncComponent(
				() => import('./FinalizeInvoicesDialog.vue'),
			);
			renderDialog(h(finalizeInvoicesDialog));
			return;
		}
	}
	if (!changePaymentMode.loading) changePaymentMode.submit({ mode });
}

function changeMethod() {
	if (team.doc.payment_method) {
		showChangeCardDialog.value = true;
	} else {
		showMessage.value = false;
		showAddCardDialog.value = true;
	}
}
</script>
