<template>
	<Dialog
		:model-value="modelValue"
		@update:model-value="(value: boolean) => emit('update:modelValue', value)"
		:options="{
			title: 'Create',
			message: 'Create a new role.',
			size: '2xl',
			actions: [
				{
					label: 'Submit',
					variant: 'solid',
					onClick: () => emit('create', title, users, resources),
				},
			],
		}"
	>
		<template #body-content>
			<div class="space-y-4">
				<div class="space-y-2 leading-relaxed">
					<div class="font-medium text-lg">Title</div>
					<FormControl
						v-model="title"
						type="text"
						size="sm"
						variant="subtle"
						placeholder="Website Manager"
					/>
				</div>
				<div class="space-y-2 leading-relaxed">
					<div class="font-medium text-lg">Users</div>
					<FormControl
						type="select"
						size="sm"
						variant="subtle"
						placeholder="hello@example.com"
						model-value=""
						:options="teamMembers(users)"
						@update:model-value="
							(u: string) => {
								users.push(u);
							}
						"
					/>
					<div class="flex gap-2 flex-wrap">
						<div
							v-for="user in users"
							class="text-base border rounded-xl px-2 py-2"
						>
							{{ user }}
						</div>
					</div>
				</div>
				<div class="space-y-2 leading-relaxed">
					<div class="font-medium text-lg">Resources</div>
					<FormControl
						type="select"
						size="sm"
						variant="subtle"
						placeholder="erpnext.frappe.cloud"
						model-value=""
						:options="resourceOptions"
						@update:model-value="
							(r: string) => {
								resources.push(
									resourceOptions.find((resource) => resource.value === r),
								);
							}
						"
					/>
					<div class="flex gap-2 flex-wrap">
						<div
							v-for="resource in resources"
							class="text-base border rounded-xl px-2 py-2"
						>
							{{ resource.document_name }}
						</div>
					</div>
				</div>
			</div>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import { Dialog, FormControl } from 'frappe-ui';
import { teamMembers, teamResources } from './data';

defineProps<{
	modelValue: boolean;
}>();

const emit = defineEmits<{
	create: [title: string, users: string[], resources: string[]];
	'update:modelValue': [value: boolean];
}>();

const title = ref('');
const users = ref<string[]>([]);
const resources = ref<any[]>([]);

const resourceOptions = computed(() => {
	return teamResources.value.filter(
		(resource) =>
			!resources.value.some(
				(r) =>
					r.document_type === resource.document_type &&
					r.document_name === resource.document_name,
			),
	);
});
</script>
