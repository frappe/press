<script setup lang="ts">
import { createResource, FormControl } from 'frappe-ui'
import { computed, inject, ref, watch } from 'vue'
import {
	getPartnerMRRCurrency,
	getPartnerMRRTargetLabel,
	type PartnerOnboardingDoc,
} from '@/onboarding/usePartnerOnboarding'

const emit = defineEmits(['continue'])
const props = defineProps<{
	form: PartnerOnboardingDoc
}>()

const team = inject('team')

const countryListResource = createResource({
	url: 'press.api.account.country_list',
	cache: 'countryList',
	auto: true,
})

const countryOptions = computed(() => {
	return (countryListResource.data || []).map((c) => ({
		label: c.name,
		value: c.name,
	}))
})

const revenueCurrencyOptions = [
	{ label: 'INR (Indian Rupees)', value: 'INR' },
	{ label: 'USD (US Dollar)', value: 'USD' },
	{ label: 'EUR (Euro)', value: 'EUR' },
]

const employeeRangeOptions = [
	{ label: '1-10', value: '1-10' },
	{ label: '11-50', value: '11-50' },
	{ label: '51-200', value: '51-200' },
	{ label: '201+', value: '201+' },
]

const certifiedEmployeesOptions = [
	{ label: '0', value: '0' },
	{ label: '1-5', value: '1-5' },
	{ label: '6-20', value: '6-20' },
	{ label: '21+', value: '21+' },
]

const submitted = ref(false)
const revenueCurrencyAutoSynced = ref(
	!props.form.revenue_currency ||
		props.form.revenue_currency ===
			getPartnerMRRCurrency(props.form.registered_country),
)

watch(
	() => team?.doc,
	(doc) => {
		if (!doc || props.form.company_name) return
		props.form.company_name =
			doc.company_name?.trim() || doc.billing_name?.trim() || ''
		if (doc.country && !props.form.registered_country) {
			props.form.registered_country = doc.country
		}
	},
	{ immediate: true },
)

watch(
	() => props.form.registered_country,
	(country) => {
		const nextCurrency = getPartnerMRRCurrency(country)

		if (!props.form.revenue_currency || revenueCurrencyAutoSynced.value) {
			props.form.revenue_currency = nextCurrency
			revenueCurrencyAutoSynced.value = true
		}
	},
	{ immediate: true },
)

// this is so stupid that I have to do it this way because the form control does not support minlength and maxlength
const companyNameMinLength = 2
const companyNameMaxLength = 140
const addressMinLength = 10
const addressMaxLength = 300
const cityMinLength = 2
const cityMaxLength = 80
const annualRevenueMaxDigits = 12

function getLengthError(
	value: string | undefined,
	label: string,
	min: number,
	max: number,
) {
	const trimmedValue = String(value || '').trim()
	if (!trimmedValue) return `${label} is required.`
	if (trimmedValue.length < min) {
		return `${label} must be at least ${min} characters.`
	}
	if (trimmedValue.length > max) {
		return `${label} must be ${max} characters or less.`
	}
	return ''
}

function getAnnualRevenueError(value: string | number | undefined) {
	const trimmedValue = String(value || '').trim()
	if (!trimmedValue) return ''
	if (!/^\d+(\.\d{1,2})?$/.test(trimmedValue)) {
		return 'Annual revenue must be a valid amount.'
	}
	if (trimmedValue.replace(/\D/g, '').length > annualRevenueMaxDigits) {
		return `Annual revenue must be ${annualRevenueMaxDigits} digits or less.`
	}
	return ''
}

const errors = computed(() => {
	if (!submitted.value) return {}
	return {
		company_name: getLengthError(
			props.form.company_name,
			'Company name',
			companyNameMinLength,
			companyNameMaxLength,
		),
		address: getLengthError(
			props.form.address,
			'Address',
			addressMinLength,
			addressMaxLength,
		),
		country: props.form.registered_country ? '' : 'Country is required.',
		headquarter_city: getLengthError(
			props.form.headquarter_city,
			'Headquarter city',
			cityMinLength,
			cityMaxLength,
		),
		annual_revenue: getAnnualRevenueError(props.form.annual_revenue),
	}
})

const currencyPrefix = computed(() => {
	const c = props.form.revenue_currency
	if (c === 'USD') return '$'
	if (c === 'EUR') return '€'
	return '₹'
})

const mrrTargetLabel = computed(() =>
	getPartnerMRRTargetLabel(props.form.registered_country),
)

function validate() {
	submitted.value = true
	return !Object.values(errors.value).some(Boolean)
}

function tryContinue() {
	if (validate()) emit('continue')
}

defineExpose({ tryContinue })
</script>

<template>
	<form
		id="company-information-form-1"
		class="flex flex-col gap-5"
		@submit.prevent="tryContinue"
	>
		<FormControl
			v-model="props.form.company_name"
			label="Registered company"
			type="text"
			size="sm"
			variant="outline"
			:minlength="companyNameMinLength"
			:maxlength="companyNameMaxLength"
			:class="{ 'has-error': errors.company_name }"
		/>
		<p v-if="errors.company_name" class="-mt-3 text-sm text-ink-red-8">
			{{ errors.company_name }}
		</p>

		<FormControl
			v-model="props.form.address"
			label="Address"
			type="text"
			size="sm"
			variant="outline"
			placeholder="Company's registered address"
			:minlength="addressMinLength"
			:maxlength="addressMaxLength"
			:class="{ 'has-error': errors.address }"
		/>
		<p v-if="errors.address" class="-mt-3 text-sm text-ink-red-8">
			{{ errors.address }}
		</p>

		<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
			<div class="flex flex-col gap-1">
				<FormControl
					v-model="props.form.registered_country"
					label="Registered country"
					type="select"
					size="sm"
					variant="outline"
					placeholder="Select"
					:options="countryOptions"
					:class="{ 'has-error': errors.country }"
				/>
				<p v-if="errors.country" class="text-sm text-ink-red-8">
					{{ errors.country }}
				</p>
			</div>

			<div class="flex flex-col gap-1">
				<FormControl
					v-model="props.form.headquarter_city"
					label="Headquarter city"
					type="text"
					size="sm"
					variant="outline"
					placeholder="Headquarter city"
					:minlength="cityMinLength"
					:maxlength="cityMaxLength"
					:class="{ 'has-error': errors.headquarter_city }"
				/>
				<p v-if="errors.headquarter_city" class="text-sm text-ink-red-8">
					{{ errors.headquarter_city }}
				</p>
			</div>
		</div>

		<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
			<div class="flex flex-col gap-1">
				<div class="flex items-center justify-between gap-2">
					<span class="text-xs text-ink-gray-6">Annual revenue</span>
					<span class="text-xs text-ink-gray-5">Optional</span>
				</div>
				<div class="relative">
					<span
						class="pointer-events-none absolute left-3 top-1/2 z-10 -translate-y-1/2 text-sm text-ink-gray-6"
					>
						{{ currencyPrefix }}
					</span>
					<FormControl
						v-model="props.form.annual_revenue"
						type="text"
						size="sm"
						variant="outline"
						:class="[
						'[&_input]:pl-7',
						{ 'has-error': errors.annual_revenue },
					]"
						placeholder="Amount"
					/>
				</div>
				<p v-if="errors.annual_revenue" class="text-sm text-ink-red-8">
					{{ errors.annual_revenue }}
				</p>
			</div>

			<div class="flex flex-col gap-1">
				<div class="flex items-center justify-between gap-2">
					<span class="text-xs text-ink-gray-6">Revenue currency</span>
					<span class="text-xs text-ink-gray-5">Optional</span>
				</div>
				<FormControl
					v-model="props.form.revenue_currency"
					type="select"
					size="sm"
					variant="outline"
					:options="revenueCurrencyOptions"
					@update:model-value="revenueCurrencyAutoSynced = false"
				/>
				<p class="text-xs leading-4 text-ink-gray-5">
					Partner MRR target for this country: {{ mrrTargetLabel }}.
				</p>
			</div>
		</div>

		<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
			<div class="flex flex-col gap-1">
				<div class="flex items-center justify-between gap-2">
					<span class="text-xs text-ink-gray-6">No. of employees</span>
					<span class="text-xs text-ink-gray-5">Optional</span>
				</div>
				<FormControl
					v-model="props.form.employee_range"
					type="select"
					size="sm"
					variant="outline"
					placeholder="Select a range"
					:options="employeeRangeOptions"
				/>
			</div>

			<div class="flex flex-col gap-1">
				<div class="flex items-center justify-between gap-2">
					<span class="text-xs text-ink-gray-6"
						>No. of certified employees</span
					>
					<span class="text-xs text-ink-gray-5">Optional</span>
				</div>
				<FormControl
					v-model="props.form.certified_employees_range"
					type="select"
					size="sm"
					variant="outline"
					placeholder="Select"
					:options="certifiedEmployeesOptions"
				/>
			</div>
		</div>
	</form>
</template>

<style scoped>
.has-error :deep(input),
.has-error :deep(button) {
	border-color: var(--outline-red-4);
}
</style>
