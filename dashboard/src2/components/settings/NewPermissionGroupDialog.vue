<template>
	<Dialog
		v-model="showDialog"
		:modelValue="true"
		:options="{ title: 'Create Permission Group' }"
	>
		<template v-slot:body-content>
			<div class="space-y-4">
				<FormControl
					label="Group Name"
					v-model="groupName"
					autocomplete="off"
					placeholder="Group Name"
				/>
			</div>
		</template>

		<template #actions>
			<Button
				class="mt-2 w-full"
				variant="solid"
				:disable="!groupName"
				:loading="addGroup.loading"
				@click="addGroup.submit({ group_name: groupName })"
			>
				Create
			</Button>
		</template>
	</Dialog>
</template>

<script setup>
import { createResource } from 'frappe-ui';
import { ref } from 'vue';
import { getTeam } from '../../data/team';

const emit = defineEmits(['groupCreated']);

const showDialog = ref(true);
const groupName = ref('');

const team = getTeam();
const addGroup = createResource({
	url: 'press.api.client.insert',
	makeParams() {
		return {
			doc: {
				doctype: 'Press Permission Group',
				team: team.doc.name,
				title: groupName.value,
			}
		};
	},
	onSuccess() {
		showDialog.value = false;
		emit('groupCreated');
	}
});
</script>
