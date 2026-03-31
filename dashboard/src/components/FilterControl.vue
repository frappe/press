<template>
	<LinkControl
		v-if="$attrs.type === 'link'"
		v-bind="$attrs"
		class="min-w-[6rem]"
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
	<div
		v-else-if="$attrs.type === 'checkbox'"
		class="[&_input+label]:text-ink-gray-5 [&_input:checked+label]:text-ink-gray-8 [&_input+label]:font-normal"
	>
		<FormControl v-bind="$attrs" />
	</div>
	<FormControl v-else v-bind="$attrs" />
	<div v-if="$attrs.type === 'date' || $attrs.type === 'datetime'"></div>
	<!-- idk what magic is it but if I remove the div datetime components cease to work -->
</template>

<script setup>
import { DatePicker, TabButtons, DateTimePicker } from 'frappe-ui';
import LinkControl from './LinkControl.vue';
import FormControl from 'frappe-ui/src/components/FormControl/FormControl.vue';
</script>
