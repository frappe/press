<script setup lang="ts">
import { createResource } from 'frappe-ui'
import { computed, ref } from 'vue'
import { getTeam } from '../../data/team'

defineEmits<{
	(e: 'success', value: { names: string; role: string }): void
}>()

const open = defineModel<boolean>()
const email = ref('')
const selectedRole = ref('Member')

const team = getTeam()

const roles = createResource({
	url: 'run_doc_method',
	auto: true,
	params: {
		method: 'get_roles',
		dt: 'Team',
		dn: team.doc.name,
	},
	transform: (d) => d.message,
})

const roleOptions = computed(() => {
	if (!roles.data) return []
	return roles.data.map((r) => ({ label: r.label, value: r.value }))
})

const close = () => {
	email.value = ''
	selectedRole.value = 'Member'
}
</script>

<template>
	<Dialog
		v-model="open"
		:options="{
			title: 'Invite users',
			icon: 'user-plus',
			actions: [
				{
					label: 'Invite',
					variant: 'solid',
					iconLeft: 'send',
					disabled: !email,
					onClick: () => {
						$emit('success', { names: email, role: selectedRole });
						$emit('update:modelValue', false);
						email = '';
						selectedRole = 'Member';
					},
				},
			],
		}"
		@close="close"
	>
		<template #body-content>
			<div class="space-y-4">
				<FormControl
					v-model="email"
					label="Email addresses"
					placeholder="name@example.com, name2@example.com"
				/>
				<FormControl
					v-if="roleOptions.length > 0"
					v-model="selectedRole"
					type="select"
					label="Role"
					:options="roleOptions"
				/>
			</div>
		</template>
	</Dialog>
</template>
