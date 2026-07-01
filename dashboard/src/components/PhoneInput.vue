<template>
	<div class="space-y-1.5">
		<label v-if="label" class="block text-xs text-ink-gray-6">
			{{ label }}
		</label>
		<div
			class="phone-control flex h-7 overflow-hidden rounded border border-outline-gray-1 focus-within:border-outline-gray-4 focus-within:ring-2 focus-within:ring-gray-400"
		>
			<Popover class="relative flex" placement="bottom-start">
				<template #target="{ togglePopover }">
					<button
						type="button"
						@click="togglePopover"
						class="flex h-full items-center gap-4 border-r border-outline-gray-1 bg-transparent px-2 text-sm text-ink-gray-8 hover:bg-surface-gray-3 focus:outline-none"
					>
						<span v-if="selectedCountry" class="flex items-center gap-1">
							<img
								:src="getFlagUrl(selectedCountry.code)"
								:alt="selectedCountry.name"
								class="h-3 w-4 object-cover"
							/>
							<span class="text-ink-gray-6">{{ selectedCountry.isd }}</span>
						</span>
						<span v-else class="text-ink-gray-5">+</span>
						<LucideChevronDown class="h-3 w-3 text-ink-gray-5" />
					</button>
				</template>
				<template #body="{ close }">
					<div
						class="mt-1 max-h-60 w-64 overflow-auto rounded-lg bg-surface-white p-1 shadow-2xl"
					>
						<input
							v-model="searchQuery"
							type="text"
							placeholder="Search country..."
							class="mb-1 w-full rounded border border-outline-gray-1 px-2 py-1.5 text-sm focus:border-outline-gray-3 focus:outline-none"
							@click.stop
						/>
						<div
							v-for="country in filteredCountries"
							:key="country.name"
							@click="selectCountry(country, close)"
							class="flex cursor-pointer items-center gap-2 rounded px-2 py-1.5 text-sm hover:bg-surface-gray-2"
							:class="{
								'bg-surface-gray-2': selectedCountry?.name === country.name,
							}"
						>
							<img
								:src="getFlagUrl(country.code)"
								:alt="country.name"
								class="h-3 w-4 object-cover"
							/>
							<span class="flex-1 truncate">{{ country.name }}</span>
							<span class="text-ink-gray-5">{{ country.isd }}</span>
						</div>
						<div
							v-if="filteredCountries.length === 0"
							class="px-2 py-1.5 text-sm text-ink-gray-5"
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
				class="h-full w-full border-0 bg-transparent px-2 text-base text-ink-gray-8 placeholder-gray-500 focus:outline-none focus:ring-0"
				@input="emitValue"
			/>
		</div>
	</div>
</template>

<script setup>
import { Popover } from 'frappe-ui'
import { computed, onMounted, ref, watch } from 'vue'
import LucideChevronDown from '~icons/lucide/chevron-down'

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
})

const emit = defineEmits(['update:modelValue'])

const searchQuery = ref('')
const phoneNumber = ref('')
const selectedCountry = ref(null)
const manuallySelectedCountry = ref(false)

const filteredCountries = computed(() => {
	if (!searchQuery.value) {
		return props.countries
	}
	const query = searchQuery.value.toLowerCase()
	return props.countries.filter(
		(c) =>
			c.name.toLowerCase().includes(query) ||
			c.isd.includes(query) ||
			c.code.toLowerCase().includes(query),
	)
})

function getFlagUrl(countryCode) {
	if (!countryCode) return ''
	return `https://flagcdn.com/w20/${countryCode.toLowerCase()}.png`
}

function selectCountry(country, close) {
	selectedCountry.value = country
	manuallySelectedCountry.value = true
	searchQuery.value = ''
	close()
	emitValue()
}

function emitValue() {
	if (selectedCountry.value && phoneNumber.value) {
		emit(
			'update:modelValue',
			`${selectedCountry.value.isd}-${phoneNumber.value}`,
		)
	} else {
		emit('update:modelValue', phoneNumber.value)
	}
}

function parseModelValue() {
	if (props.modelValue && props.modelValue.includes('-')) {
		const [isd, number] = props.modelValue.split('-')
		phoneNumber.value = number || ''
		const country = findCountry(isd)
		if (country) {
			selectedCountry.value = country
		}
	} else {
		phoneNumber.value = props.modelValue || ''
	}
}

function findCountry(country) {
	if (!country || props.countries.length === 0) {
		return null
	}

	const countryValue = String(country).toLowerCase()
	return props.countries.find((c) => {
		return (
			c.name?.toLowerCase() === countryValue ||
			c.code?.toLowerCase() === countryValue ||
			c.isd === country
		)
	})
}

function setCountryFromHint(country) {
	const nextCountry = findCountry(country)
	if (nextCountry && nextCountry.name !== selectedCountry.value?.name) {
		selectedCountry.value = nextCountry
		if (phoneNumber.value) {
			emitValue()
		}
	}
}

watch(
	() => props.country,
	(newCountry) => {
		if (newCountry && !manuallySelectedCountry.value) {
			setCountryFromHint(newCountry)
		}
	},
	{ immediate: true },
)

watch(
	() => props.countries,
	() => {
		parseModelValue()
		if (props.country && !manuallySelectedCountry.value) {
			setCountryFromHint(props.country)
		}
	},
)

onMounted(() => {
	parseModelValue()
	if (props.country && !manuallySelectedCountry.value) {
		setCountryFromHint(props.country)
	}
})
</script>

<style scoped>
.has-error .phone-control {
	border-color: var(--outline-red-3);
}
</style>
