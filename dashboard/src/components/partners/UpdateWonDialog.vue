<template>
	<Dialog v-model="show" :options="{ title: 'Add Won Details' }">
		<template #body-content>
			<div class="flex flex-col gap-5">
				<FormControl
					v-model="resource_type"
					label="Resource Type"
					type="select"
					name="resource_type"
					:options="[
						{ label: 'Site', value: 'Site' },
						{ label: 'Server Name', value: 'Server' },
						{ label: 'Account Email ID', value: 'Team' },
					]"
					:required="true"
				/>
				<FormControl
					v-if="resource_type == 'Site'"
					v-model="site_url"
					label="Site URL"
					type="data"
					name="site_url"
					:required="true"
					placeholder="e.g. example.m.frappe.cloud"
				/>
				<FormControl
					v-if="resource_type == 'Server'"
					v-model="server_name"
					label="Server Name"
					type="data"
					name="server_name"
					placeholder="e.g. f1-mumbai.frappe.cloud"
					:required="true"
				/>
				<FormControl
					v-if="resource_type == 'Team'"
					v-model="team_name"
					label="Account Email ID"
					type="data"
					name="team_name"
					placeholder="e.g. jondoe@example.com"
					:required="true"
				/>
				<ErrorMessage :message="errorMessage" />
				<Button variant="solid" @click="() => updateStatus.submit()"
					>Submit</Button
				>
			</div>
		</template>
	</Dialog>
</template>
<script setup>
import { Dialog, FormControl, createResource } from 'frappe-ui';
import { ref, defineEmits, watch } from 'vue';
import { DashboardError } from '../../utils/error';

const emit = defineEmits(['update']);
const show = defineModel();
const props = defineProps({
	lead_id: {
		type: String,
		required: true,
	},
});

const site_url = ref();
const server_name = ref();
const team_name = ref();
const resource_type = ref();
const errorMessage = ref('');
const updateStatus = createResource({
	url: 'press.api.partner.update_lead_status',
	makeParams: () => {
		return {
			lead_name: props.lead_id,
			status: 'Won',
			site_url: site_url.value,
			server_name: server_name.value,
			team_name: team_name.value,
		};
	},
	validate: () => {
		if (
			site_url.value === undefined ||
			server_name.value === undefined ||
			team_name.value === undefined
		) {
			let error = 'Please fill all the required fields';
			errorMessage.value = error;
			throw new DashboardError(error);
		}
	},
	onSuccess: () => {
		emit('update');
		show.value = false;
	},
	onError: (e) => {
		errorMessage.value = e.messages[0] || 'Failed to update lead as won';
	},
});

watch(resource_type, () => {
	site_url.value = '';
	server_name.value = '';
	team_name.value = '';
});
</script>
