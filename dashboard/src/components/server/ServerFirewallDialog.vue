<template>
	<Dialog
		:options="{
			title: 'Add Firewall Rule',
			size: 'lg',
			icon: {
				name: 'shield',
				appearance: 'info',
			},
			actions: [
				{
					label: 'Submit',
					variant: 'solid',
					onClick: onSubmit,
				},
			],
		}"
		:model-value="modelValue"
		@update:model-value="$emit('update:modelValue', $event)"
		@close="onClose"
	>
		<template #body-content>
			<div class="space-y-4">
				<FormControl
					v-model="values.source"
					label="Source"
					placeholder="1.2.3.4"
					type="text"
					size="sm"
					variant="subtle"
				/>
				<FormControl
					v-model="values.destination"
					label="Destination"
					placeholder="1.2.3.4"
					type="text"
					size="sm"
					variant="subtle"
				/>
				<FormControl
					v-model="values.protocol"
					label="Protocol"
					type="select"
					:options="[
						{
							label: 'TCP',
							value: 'TCP',
						},
						{
							label: 'UDP',
							value: 'UDP',
						},
					]"
					size="sm"
					variant="subtle"
				/>
				<FormControl
					v-model="values.action"
					label="Action"
					type="select"
					:options="[
						{
							label: 'Block',
							value: 'Block',
						},
						{
							label: 'Allow',
							value: 'Allow',
						},
					]"
					size="sm"
					variant="subtle"
				/>
			</div>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import { reactive } from 'vue';

defineProps<{
	modelValue: boolean;
}>();

const emit = defineEmits<{
	(event: 'update:modelValue', open: boolean): void;
	(
		event: 'submit',
		values: {
			source: string;
			destination: string;
			protocol: string;
			action: string;
		},
	): void;
}>();

const values = reactive({
	source: '',
	destination: '',
	protocol: 'TCP',
	action: 'Block',
});

const onClose = () => {
	values.source = '';
	values.destination = '';
	values.protocol = 'TCP';
	values.action = 'Block';
	emit('update:modelValue', false);
};

const onSubmit = () => {
	emit('submit', values);
	onClose();
};
</script>
