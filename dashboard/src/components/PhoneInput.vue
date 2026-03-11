<template>
	<div class="space-y-1.5">
		<label v-if="label" class="block text-xs text-gray-600">
			{{ label }}
		</label>
		<div class="flex">
			<Popover class="relative" placement="bottom-start">
				<template #target="{ togglePopover }">
					<button
						type="button"
						@click="togglePopover"
						class="flex h-7 items-center gap-1 rounded-l border border-r-0 border-gray-100 bg-gray-100 px-2 text-sm text-gray-800 hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-gray-400"
					>
						<span v-if="selectedCountry" class="flex items-center gap-1">
							<img
								:src="getFlagUrl(selectedCountry.code)"
								:alt="selectedCountry.name"
								class="h-3 w-4 object-cover"
							/>
							<span class="text-gray-600">{{ selectedCountry.isd }}</span>
						</span>
						<span v-else class="text-gray-500">+</span>
						<FeatherIcon name="chevron-down" class="h-3 w-3 text-gray-500" />
					</button>
				</template>
				<template #body="{ close }">
					<div
						class="mt-1 max-h-60 w-64 overflow-auto rounded-lg bg-white p-1 shadow-2xl"
					>
						<input
							v-model="searchQuery"
							type="text"
							placeholder="Search country..."
							class="mb-1 w-full rounded border border-gray-200 px-2 py-1.5 text-sm focus:border-gray-400 focus:outline-none"
							@click.stop
						/>
						<div
							v-for="country in filteredCountries"
							:key="country.name"
							@click="selectCountry(country, close)"
							class="flex cursor-pointer items-center gap-2 rounded px-2 py-1.5 text-sm hover:bg-gray-100"
							:class="{
								'bg-gray-100': selectedCountry?.name === country.name,
							}"
						>
							<img
								:src="getFlagUrl(country.code)"
								:alt="country.name"
								class="h-3 w-4 object-cover"
							/>
							<span class="flex-1 truncate">{{ country.name }}</span>
							<span class="text-gray-500">{{ country.isd }}</span>
						</div>
						<div
							v-if="filteredCountries.length === 0"
							class="px-2 py-1.5 text-sm text-gray-500"
						>
							No countries found
						</div>
					</div>
				</template>
			</Popover>
			<input
				type="tel"
				v-model="phoneNumber"
				:placeholder="selectedCountry?.example || placeholder"
				class="h-7 w-full rounded-r border border-gray-100 bg-gray-100 px-2 text-base text-gray-800 placeholder-gray-500 focus:border-gray-500 focus:bg-white focus:outline-none focus:ring-0 focus-visible:ring-2 focus-visible:ring-gray-400"
				@input="emitValue"
			/>
		</div>
	</div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue';
import { Popover } from 'frappe-ui';

const props = defineProps({
	modelValue: {
		type: String,
		default: '',
	},
	label: {
		type: String,
		default: '',
	},
	placeholder: {
		type: String,
		default: '9876543210',
	},
	countries: {
		type: Array,
		default: () => [],
	},
	country: {
		type: String,
		default: '',
	},
});

const emit = defineEmits(['update:modelValue']);

const searchQuery = ref('');
const phoneNumber = ref('');
const selectedCountry = ref(null);
const manuallySelectedCountry = ref(false);

const filteredCountries = computed(() => {
	if (!searchQuery.value) {
		return props.countries;
	}
	const query = searchQuery.value.toLowerCase();
	return props.countries.filter(
		(c) =>
			c.name.toLowerCase().includes(query) ||
			c.isd.includes(query) ||
			c.code.toLowerCase().includes(query),
	);
});

function getFlagUrl(countryCode) {
	if (!countryCode) return '';
	return `https://flagcdn.com/w20/${countryCode.toLowerCase()}.png`;
}

function selectCountry(country, close) {
	selectedCountry.value = country;
	manuallySelectedCountry.value = true;
	searchQuery.value = '';
	close();
	emitValue();
}

function emitValue() {
	if (selectedCountry.value && phoneNumber.value) {
		emit(
			'update:modelValue',
			`${selectedCountry.value.isd}-${phoneNumber.value}`,
		);
	} else {
		emit('update:modelValue', phoneNumber.value);
	}
}

function parseModelValue() {
	if (props.modelValue && props.modelValue.includes('-')) {
		const [isd, number] = props.modelValue.split('-');
		phoneNumber.value = number || '';
		const country = props.countries.find((c) => c.isd === isd);
		if (country) {
			selectedCountry.value = country;
		}
	} else {
		phoneNumber.value = props.modelValue || '';
	}
}

function setCountryFromName(countryName) {
	if (countryName && props.countries.length > 0) {
		const country = props.countries.find((c) => c.name === countryName);
		if (country) {
			selectedCountry.value = country;
		}
	}
}

watch(
	() => props.country,
	(newCountry) => {
		if (newCountry && !manuallySelectedCountry.value) {
			setCountryFromName(newCountry);
		}
	},
	{ immediate: true },
);

watch(
	() => props.countries,
	() => {
		if (props.country && !manuallySelectedCountry.value) {
			setCountryFromName(props.country);
		}
	},
);

onMounted(() => {
	parseModelValue();
	if (props.country && !manuallySelectedCountry.value) {
		setCountryFromName(props.country);
	}
});
</script>
