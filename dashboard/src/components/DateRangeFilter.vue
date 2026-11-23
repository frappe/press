<template>
	<DateRangePicker :modelValue="pickerValue" @update:modelValue="onPick">
		<template #target="{ togglePopover }">
			<Dropdown :options="dropdownOptions(togglePopover)">
				<Button class="w-full justify-between">
					<span :class="modelValue ? 'text-ink-gray-8' : 'text-ink-gray-4'">
						{{ label }}
					</span>
					<template #suffix>
						<lucide-chevron-down class="h-4 w-4 text-ink-gray-5" />
					</template>
				</Button>
			</Dropdown>
		</template>
	</DateRangePicker>
</template>

<script>
import { Button, DateRangePicker, Dropdown } from 'frappe-ui';
import dayjs, { dayjsIST, dayjsLocal } from '../utils/dayjs';

const DATE = 'YYYY-MM-DD';
const SERVER_DATETIME = 'YYYY-MM-DD HH:mm:ss.SSS';

// Each preset ends today, so its range moves forward with the calendar
const PRESETS = [
	{ label: 'Today', days: 1 },
	{ label: 'Last 7 days', days: 7 },
	{ label: 'Last 14 days', days: 14 },
	{ label: 'Last 30 days', days: 30 },
	{ label: 'Last 90 days', days: 90 },
];

// The user picks days in their own timezone, but the server stores
// datetimes in Asia/Calcutta. Convert the bounds of each day.
function dayStart(date) {
	return dayjsIST(dayjs(date).startOf('day')).format(SERVER_DATETIME);
}

function dayEnd(date) {
	return dayjsIST(dayjs(date).endOf('day')).format(SERVER_DATETIME);
}

function localDate(serverDatetime) {
	return dayjsLocal(serverDatetime).format(DATE);
}

function presetStart(preset) {
	return dayStart(dayjs().subtract(preset.days - 1, 'day'));
}

// A preset has no upper bound, so the jobs from after midnight still show
function presetFilter(preset) {
	return ['>=', presetStart(preset)];
}

export default {
	name: 'DateRangeFilter',
	props: {
		// A `between` or `>=` filter on a datetime field
		modelValue: { type: [Array, String], default: '' },
		placeholder: { type: String, default: 'Date' },
	},
	emits: ['update:modelValue'],
	components: {
		Button,
		DateRangePicker,
		Dropdown,
	},
	data() {
		return { activePreset: null };
	},
	mounted() {
		this.activePreset = this.matchingPreset();
		// Move the preset to the new day if the page stays open past midnight
		this.timer = setInterval(() => {
			if (!this.activePreset) return;
			const filter = presetFilter(this.activePreset);
			if (filter[1] !== this.modelValue?.[1]) {
				this.$emit('update:modelValue', filter);
			}
		}, 60 * 1000);
	},
	beforeUnmount() {
		clearInterval(this.timer);
	},
	watch: {
		modelValue() {
			if (!this.modelValue) this.activePreset = null;
		},
	},
	computed: {
		pickerValue() {
			const [operator, value] = this.modelValue || [];
			if (operator === '>=') {
				return `${localDate(value)},${dayjs().format(DATE)}`;
			}
			if (operator === 'between') {
				return value.map(localDate).join(',');
			}
			return '';
		},
		label() {
			const [operator, value] = this.modelValue || [];
			if (operator === '>=') {
				const preset = this.activePreset || this.matchingPreset();
				if (preset) return preset.label;
				return `Since ${dayjsLocal(value).format('D MMM YYYY')}`;
			}
			if (operator === 'between') {
				const [from, to] = value.map(dayjsLocal);
				if (from.isSame(to, 'day')) return from.format('D MMM YYYY');
				return `${from.format('D MMM')} – ${to.format('D MMM YYYY')}`;
			}
			return this.placeholder;
		},
	},
	methods: {
		matchingPreset() {
			const [operator, value] = this.modelValue || [];
			if (operator !== '>=') return null;
			return PRESETS.find((preset) => presetStart(preset) === value) || null;
		},
		onPick(value) {
			this.activePreset = null;
			if (!value) return this.$emit('update:modelValue', '');
			const [from, to] = value.split(',');
			this.$emit('update:modelValue', ['between', [dayStart(from), dayEnd(to)]]);
		},
		dropdownOptions(togglePopover) {
			return [
				...PRESETS.map((preset) => ({
					label: preset.label,
					onClick: () => {
						this.activePreset = preset;
						this.$emit('update:modelValue', presetFilter(preset));
					},
				})),
				{
					label: 'Custom range',
					// Wait for the menu to close, or its focus change closes the calendar
					onClick: () => setTimeout(togglePopover),
				},
				{
					label: 'Clear',
					condition: () => !!this.modelValue,
					onClick: () => this.$emit('update:modelValue', ''),
				},
			];
		},
	},
};
</script>
