<template>
	<div class="flex flex-col gap-4">
		<div class="flex flex-col rounded-lg text-base text-gray-900 shadow">
			<div class="flex flex-col gap-2.5 px-4 py-3">
				<div class="flex items-center justify-between">
					<div class="flex flex-col gap-1.5">
						<div class="text-lg font-semibold">Recurring Charges</div>
						<div class="text-gray-700">
							<span>Next charge date — </span>
							<span>{{ currentMonthEnd() }}</span>
						</div>
					</div>
				</div>
				<div class="flex items-center justify-between">
					<div class="flex gap-2 text-gray-700">
						<lucide-credit-card class="h-4 w-4" />
						<div>
							<span>Current billing amount so far is </span>
							<span class="font-medium text-gray-900">
								{{ currency }} {{ currentBillingAmount?.toFixed(2) || '0.00' }}
							</span>
						</div>
					</div>
					<div>
						<Button label="View Invoice" @click="showInvoiceDialog = true" />
					</div>
				</div>
			</div>
			<div
				v-if="unpaidAmount.data"
				class="m-1.5 flex items-center justify-between rounded-lg bg-gray-50 px-2.5 py-2"
			>
				<div class="flex h-7 items-center gap-2 text-gray-800">
					<lucide-receipt class="h-4 w-4" />
					<div>
						<span>Unpaid amount is </span>
						<span>{{ currency }} {{ unpaidAmount.data?.toFixed(2) }}</span>
					</div>
				</div>
				<div>
					<Button variant="solid" label="Pay now" @click="payNow" />
				</div>
			</div>
		</div>
		<AddPrepaidCreditsDialog
			v-if="showAddPrepaidCreditsDialog"
			v-model="showAddPrepaidCreditsDialog"
			@success="upcomingInvoice.reload()"
		/>
		<UpcomingInvoiceDialog v-model="showInvoiceDialog" />
	</div>
</template>
<script setup>
import AddPrepaidCreditsDialog from './AddPrepaidCreditsDialog.vue';
import UpcomingInvoiceDialog from './UpcomingInvoiceDialog.vue';
import { Button, createResource } from 'frappe-ui';
import { ref, computed, inject } from 'vue';
import { confirmDialog } from '../../utils/components';
import router from '../../router';

const team = inject('team');
const { currentBillingAmount, upcomingInvoice, unpaidInvoices } =
	inject('billing');

const showAddPrepaidCreditsDialog = ref(false);
const showInvoiceDialog = ref(false);

const currency = computed(() => (team.doc.currency == 'INR' ? '₹' : '$'));

const unpaidAmount = createResource({
	url: 'press.api.billing.total_unpaid_amount',
	cache: 'unpaidAmount',
	auto: true,
});

const currentMonthEnd = () => {
	const date = new Date();
	const lastDay = new Date(date.getFullYear(), date.getMonth() + 1, 0);
	return lastDay.toLocaleDateString('en-US', {
		day: 'numeric',
		month: 'short',
		year: 'numeric',
	});
};

function payNow() {
	team.doc.payment_mode == 'Prepaid Credits'
		? (showAddPrepaidCreditsDialog.value = true)
		: payUnpaidInvoices();
}

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
		let invoice = _unpaidInvoices;
		if (invoice.stripe_invoice_url && team.doc.payment_mode === 'Card') {
			window.open(
				`/api/method/press.api.client.run_doc_method?dt=Invoice&dn=${invoice.name}&method=stripe_payment_url`,
			);
		} else {
			showAddPrepaidCreditsDialog.value = true;
		}
	}
}
</script>
