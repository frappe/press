<template>
	<DateRangePicker
		:modelValue="modelValue"
		@update:modelValue="(value) => $emit('update:modelValue', value)"
	>
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
import dayjs from '../utils/dayjs';

const FORMAT = 'YYYY-MM-DD';

// Each preset ends today, so its range moves forward with the calendar
const PRESETS = [
	{ label: 'Today', days: 1 },
	{ label: 'Last 7 days', days: 7 },
	{ label: 'Last 14 days', days: 14 },
	{ label: 'Last 30 days', days: 30 },
	{ label: 'Last 90 days', days: 90 },
];

function presetValue(days) {
	const today = dayjs();
	const from = today.subtract(days - 1, 'day');
	return `${from.format(FORMAT)},${today.format(FORMAT)}`;
}

export default {
	name: 'DateRangeFilter',
	props: {
		modelValue: { type: String, default: '' },
		placeholder: { type: String, default: 'Date' },
	},
	emits: ['update:modelValue'],
	components: {
		Button,
		DateRangePicker,
		Dropdown,
	},
	computed: {
		label() {
			if (!this.modelValue) return this.placeholder;
			const preset = PRESETS.find(
				(p) => presetValue(p.days) === this.modelValue,
			);
			if (preset) return preset.label;
			const [from, to] = this.modelValue.split(',');
			if (from === to) return dayjs(from).format('D MMM YYYY');
			return `${dayjs(from).format('D MMM')} – ${dayjs(to).format('D MMM YYYY')}`;
		},
	},
	methods: {
		dropdownOptions(togglePopover) {
			return [
				...PRESETS.map((preset) => ({
					label: preset.label,
					onClick: () =>
						this.$emit('update:modelValue', presetValue(preset.days)),
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
