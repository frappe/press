<template>
	<Dialog
		v-model="props.showInvoiceDialog"
		:options="{
			size: '3xl',
			title: 'Total usage for this month',
		}"
	>
		<template #body-content>
			<template v-if="upcomingInvoice.data.upcoming_invoice">
				<div
					v-if="upcomingInvoice.data.upcoming_invoice.status === 'Empty'"
					class="text-base text-gray-600"
				>
					Nothing to show
				</div>
				<InvoiceTable
					v-else
					:invoiceId="upcomingInvoice.data.upcoming_invoice.name"
				/>
			</template>
			<template v-else>
				<div class="text-base text-gray-600">Nothing to show</div>
			</template>
		</template>
	</Dialog>
</template>

<script setup>
import { inject, ref } from 'vue';
import InvoiceTable from '../InvoiceTable.vue';

const { upcomingInvoice } = inject('billing');
const props = defineProps({
	showInvoiceDialog: Boolean,
});
</script>
