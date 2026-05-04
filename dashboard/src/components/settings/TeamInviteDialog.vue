<script setup lang="ts">
import { ref } from 'vue';

defineEmits<{
	(e: 'success', email: string): void;
}>();

const open = defineModel<boolean>();
const email = ref('');
</script>

<template>
	<Dialog
		v-model="open"
		:options="{
			title: 'Invite team members',
			actions: [
				{
					label: 'Invite',
					variant: 'solid',
					iconLeft: 'send',
					onClick: () => {
						$emit('success', email);
						$emit('update:modelValue', false);
						email = '';
					},
				},
			],
		}"
		@close="email = ''"
	>
		<template #body-content>
			<div class="space-y-4">
				<FormControl
					v-model="email"
					label="Email addresses"
					placeholder="name@example.com, name2@example.com"
				/>
			</div>
		</template>
	</Dialog>
</template>
