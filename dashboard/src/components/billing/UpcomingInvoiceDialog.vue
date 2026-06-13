<template>
	<Dialog
		v-model="props.showInvoiceDialog"
		size="3xl"
		title="Total usage for this month"
	>
		<template v-if="upcomingInvoice.data.upcoming_invoice">
			<div
				v-if="upcomingInvoice.data.upcoming_invoice.status === 'Empty'"
				class="text-base text-ink-gray-6"
			>
				Nothing to show
			</div>
			<InvoiceTable
				v-else
				:invoiceId="upcomingInvoice.data.upcoming_invoice.name"
			/>
		</template>
		<template v-else>
			<div class="text-base text-ink-gray-6">Nothing to show</div>
		</template>
	</Dialog>
</template>

<script setup>
import { inject, ref } from 'vue'
import InvoiceTable from '../InvoiceTable.vue'

const { upcomingInvoice } = inject('billing')
const props = defineProps({
	showInvoiceDialog: Boolean,
})
</script>
