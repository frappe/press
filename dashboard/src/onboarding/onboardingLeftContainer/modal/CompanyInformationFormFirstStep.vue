<script setup>
import { computed, reactive, ref, inject, watch } from 'vue';
import { FormControl, createResource } from 'frappe-ui';

const emit = defineEmits(['continue']);

const team = inject('team');

const countryListResource = createResource({
	url: 'press.api.account.country_list',
	cache: 'countryList',
	auto: true,
});

const countryOptions = computed(() => {
	return (countryListResource.data || []).map((c) => ({
		label: c.name,
		value: c.name,
	}));
});

const CITIES_BY_COUNTRY = {
	India: [
		'Mumbai',
		'Delhi',
		'Bangalore',
		'Hyderabad',
		'Chennai',
		'Pune',
		'Kolkata',
		'Ahmedabad',
	],
};

const cityOptions = computed(() => {
	const list = CITIES_BY_COUNTRY[form.country];
	if (!list?.length) return [];
	return list.map((name) => ({ label: name, value: name }));
});

const revenueCurrencyOptions = [
	{ label: 'INR (Indian Rupees)', value: 'INR' },
	{ label: 'USD (US Dollar)', value: 'USD' },
	{ label: 'EUR (Euro)', value: 'EUR' },
];

const employeeRangeOptions = [
	{ label: '1-10', value: '1-10' },
	{ label: '11-50', value: '11-50' },
	{ label: '51-200', value: '51-200' },
	{ label: '201+', value: '201+' },
];

const certifiedEmployeesOptions = [
	{ label: '0', value: '0' },
	{ label: '1-5', value: '1-5' },
	{ label: '6-20', value: '6-20' },
	{ label: '21+', value: '21+' },
];

const form = reactive({
	company_name: '',
	address: '',
	country: '',
	headquarter_city: '',
	annual_revenue: '',
	revenue_currency: 'INR',
	employee_range: '',
	certified_employees_range: '',
});

watch(
	() => team?.doc,
	(doc) => {
		if (!doc || form.company_name) return;
		form.company_name =
			doc.company_name?.trim() || doc.billing_name?.trim() || '';
		if (doc.country && !form.country) {
			form.country = doc.country;
		}
	},
	{ immediate: true },
);

const submitted = ref(false);

const errors = computed(() => {
	if (!submitted.value) return {};
	return {
		company_name: !form.company_name?.trim(),
		address: !form.address?.trim(),
		country: !form.country,
		headquarter_city: !form.headquarter_city?.trim(),
	};
});

const currencyPrefix = computed(() => {
	const c = form.revenue_currency;
	if (c === 'USD') return '$';
	if (c === 'EUR') return '€';
	return '₹';
});

function validate() {
	submitted.value = true;
	return !Object.values(errors.value).some(Boolean);
}

function tryContinue() {
	if (validate()) emit('continue');
}

defineExpose({ tryContinue });
</script>

<template>
	<form
		id="company-information-form-1"
		class="flex flex-col gap-5"
		@submit.prevent="tryContinue"
	>
		<FormControl
			v-model="form.company_name"
			label="Company name"
			type="text"
			size="sm"
			variant="outline"
			:class="{ 'has-error': errors.company_name }"
		/>

		<FormControl
			v-model="form.address"
			label="Address"
			type="text"
			size="sm"
			variant="outline"
			placeholder="Company's registered address"
			:class="{ 'has-error': errors.address }"
		/>

		<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
			<FormControl
				v-model="form.country"
				label="Country"
				type="select"
				size="sm"
				variant="outline"
				placeholder="Select"
				:options="countryOptions"
				:class="{ 'has-error': errors.country }"
			/>

			<FormControl
				v-if="cityOptions.length"
				v-model="form.headquarter_city"
				label="Headquarter City"
				type="select"
				size="sm"
				variant="outline"
				placeholder="Select city"
				:options="cityOptions"
				:class="{ 'has-error': errors.headquarter_city }"
			/>
			<FormControl
				v-else
				v-model="form.headquarter_city"
				label="Headquarter City"
				type="text"
				size="sm"
				variant="outline"
				placeholder="Headquarter city"
				:class="{ 'has-error': errors.headquarter_city }"
			/>
		</div>

		<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
			<div class="flex flex-col gap-1">
				<div class="flex items-center justify-between gap-2">
					<span class="text-xs text-gray-600">Annual Revenue</span>
					<span class="text-xs text-ink-gray-5">Optional</span>
				</div>
				<div class="relative">
					<span
						class="pointer-events-none absolute left-3 top-1/2 z-10 -translate-y-1/2 text-sm text-ink-gray-6"
					>
						{{ currencyPrefix }}
					</span>
					<FormControl
						v-model="form.annual_revenue"
						type="text"
						size="sm"
						variant="outline"
						class="[&_input]:pl-7"
						placeholder="Amount"
					/>
				</div>
			</div>

			<div class="flex flex-col gap-1">
				<div class="flex items-center justify-between gap-2">
					<span class="text-xs text-gray-600">Revenue currency</span>
					<span class="text-xs text-ink-gray-5">Optional</span>
				</div>
				<FormControl
					v-model="form.revenue_currency"
					type="select"
					size="sm"
					variant="outline"
					:options="revenueCurrencyOptions"
				/>
			</div>
		</div>

		<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
			<div class="flex flex-col gap-1">
				<div class="flex items-center justify-between gap-2">
					<span class="text-xs text-gray-600">No. of employees</span>
					<span class="text-xs text-ink-gray-5">Optional</span>
				</div>
				<FormControl
					v-model="form.employee_range"
					type="select"
					size="sm"
					variant="outline"
					placeholder="Select a range"
					:options="employeeRangeOptions"
				/>
			</div>

			<div class="flex flex-col gap-1">
				<div class="flex items-center justify-between gap-2">
					<span class="text-xs text-gray-600">No. of certified employees</span>
					<span class="text-xs text-ink-gray-5">Optional</span>
				</div>
				<FormControl
					v-model="form.certified_employees_range"
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
