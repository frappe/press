<script setup lang="ts">
import { FormControl } from 'frappe-ui'
import { computed } from 'vue'
import type { PartnerOnboardingDoc } from '@/onboarding/usePartnerOnboarding'

const emit = defineEmits(['continue'])
const props = defineProps<{
	form: PartnerOnboardingDoc
}>()

const verticalOptions = [
	{ label: 'Manufacturing', value: 'Manufacturing' },
	{ label: 'Retail', value: 'Retail' },
	{ label: 'Services', value: 'Services' },
	{ label: 'Banking and Finance', value: 'Banking and Finance' },
	{ label: 'Distribution and Trading', value: 'Distribution and Trading' },
	{ label: 'Hospitality', value: 'Hospitality' },
	{ label: 'Real Estate', value: 'Real Estate' },
	{ label: 'Automotive', value: 'Automotive' },
	{ label: 'Government', value: 'Government' },
	{ label: 'Education', value: 'Education' },
	{ label: 'Healthcare', value: 'Healthcare' },
	{ label: 'Non-profit', value: 'Non-profit' },
	{ label: 'Other', value: 'Other' },
]

const customerRangeOptions = [
	{ label: '1-10', value: '1-10' },
	{ label: '11-50', value: '11-50' },
	{ label: '51-200', value: '51-200' },
	{ label: '201+', value: '201+' },
]

const verticalsServed = computed<string[]>({
	get() {
		const value = props.form.verticals_served
		if (!value) return []
		return String(value)
			.split(',')
			.map((vertical) => vertical.trim())
			.filter(Boolean)
	},
	set(value) {
		props.form.verticals_served = value.join(', ')
	},
})

function tryContinue() {
	emit('continue')
}

defineExpose({ tryContinue })
</script>

<template>
	<form
		id="company-information-form-2"
		class="flex flex-col gap-5"
		@submit.prevent="tryContinue"
	>
		<div class="flex flex-col gap-1">
			<div class="flex items-center justify-between gap-2">
				<span class="text-xs text-ink-gray-6">Verticals served</span>
				<span class="text-xs text-ink-gray-5">Optional</span>
			</div>
			<FormControl
				v-model="verticalsServed"
				type="select"
				size="sm"
				variant="outline"
				placeholder="Select"
				:options="verticalOptions"
				multiple
			/>
		</div>

		<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
			<div class="flex flex-col gap-1">
				<div class="flex items-center justify-between gap-2">
					<span class="text-xs text-ink-gray-6">No. of customers</span>
					<span class="text-xs text-ink-gray-5">Optional</span>
				</div>
				<FormControl
					v-model="props.form.customer_count_range"
					type="select"
					size="sm"
					variant="outline"
					placeholder="Select"
					:options="customerRangeOptions"
				/>
			</div>

			<div class="flex flex-col gap-1">
				<div class="flex items-center justify-between gap-2">
					<span class="text-xs text-ink-gray-6">No. of ERPNext customers</span>
					<span class="text-xs text-ink-gray-5">Optional</span>
				</div>
				<FormControl
					v-model="props.form.erpnext_customer_count_range"
					type="select"
					size="sm"
					variant="outline"
					placeholder="Select"
					:options="customerRangeOptions"
				/>
			</div>
		</div>
	</form>
</template>
