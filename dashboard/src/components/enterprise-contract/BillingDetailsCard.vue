<template>
	<div class="rounded-md border border-outline-gray-3 p-4 text-base">
		<div
			v-if="hasBillingAddress"
			class="flex items-start justify-between gap-4"
		>
			<div class="space-y-1">
				<div class="font-medium text-ink-gray-9">
					{{ details.billing_name }}
				</div>
				<div class="text-ink-gray-7">{{ addressLine }}</div>
				<div v-if="gstin" class="text-ink-gray-7">GSTIN: {{ gstin }}</div>
			</div>
			<Button label="Edit" @click="showDialog = true" />
		</div>
		<div v-else class="flex items-center justify-between gap-4">
			<div class="flex items-center gap-2 text-ink-gray-8">
				<LucideCircleAlert class="h-4 w-4 shrink-0 text-ink-amber-3" />
				Add your billing details before you place the order.
			</div>
			<Button
				variant="solid"
				label="Add billing details"
				@click="showDialog = true"
			/>
		</div>
	</div>
	<BillingDetailsDialog
		v-if="showDialog"
		v-model="showDialog"
		@success="team.reload()"
	/>
</template>

<script setup>
import { Button } from 'frappe-ui'
import { computed, ref } from 'vue'
import { getTeam } from '../../data/team'
import BillingDetailsDialog from '../billing/BillingDetailsDialog.vue'

const team = getTeam()
const showDialog = ref(false)

const details = computed(() => team.doc.billing_details || {})
const hasBillingAddress = computed(() => Boolean(details.value.name))
const gstin = computed(() =>
	details.value.gstin === 'Not Applicable' ? '' : details.value.gstin,
)
const addressLine = computed(() => {
	const d = details.value
	return [
		d.address_line1,
		d.address_line2,
		d.city,
		d.state,
		d.pincode,
		d.country,
	]
		.filter(Boolean)
		.join(', ')
})
</script>
