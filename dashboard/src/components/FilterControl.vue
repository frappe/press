<template>
	<LinkControl
		v-if="$attrs.type === 'link'"
		v-bind="$attrs"
		class="min-w-[6rem]"
    :openOnClick="true"
	/>
	<TabButtons
		v-else-if="$attrs.type === 'tab'"
		v-bind="{ ...$attrs, buttons: $attrs.options.map((o) => ({ label: o })) }"
	/>
	<DatePicker
		v-else-if="$attrs.type === 'date'"
		v-bind="{ ...$attrs, type: undefined }"
	/>
	<DateTimePicker
		v-else-if="$attrs.type === 'datetime'"
		v-bind="{ ...$attrs, type: undefined }"
	/>
	<DateRangeFilter
		v-else-if="$attrs.type === 'daterange'"
		v-bind="{
			...$attrs,
			type: undefined,
			modelValue: toRangeString($attrs.modelValue),
			'onUpdate:modelValue': (value) =>
				$attrs['onUpdate:modelValue']?.(toBetween(value)),
		}"
	/>
	<div
		v-else-if="$attrs.type === 'checkbox'"
		class="[&_input+label]:text-ink-gray-5 [&_input:checked+label]:text-ink-gray-8 [&_input+label]:font-normal"
	>
		<FormControl v-bind="$attrs" />
	</div>
	<FormControl v-else v-bind="$attrs" />
	<div
		v-if="
			$attrs.type === 'date' ||
			$attrs.type === 'datetime' ||
			$attrs.type === 'daterange'
		"
	></div>
	<!-- idk what magic is it but if I remove the div datetime components cease to work -->
</template>

<script setup>
import { DatePicker, TabButtons, DateTimePicker, FormControl } from 'frappe-ui';
import DateRangeFilter from './DateRangeFilter.vue';
import LinkControl from './LinkControl.vue';

// A date range filter is stored as a `between` filter. The bounds cover the
// whole of both days, because `between` compares datetimes as they are.
function toBetween(value) {
	if (!value) return '';
	const [from, to] = value.split(',');
	return ['between', [`${from} 00:00:00`, `${to} 23:59:59.999999`]];
}

function toRangeString(value) {
	if (!Array.isArray(value)) return '';
	return value[1].map((bound) => bound.split(' ')[0]).join(',');
}
</script>
