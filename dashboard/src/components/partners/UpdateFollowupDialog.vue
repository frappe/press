<template>
	<Dialog v-model="show" :options="{ title: 'Update Followup Details' }">
		<template #body-content>
			<div class="flex flex-col gap-4">
				<div
					v-for="section in sections"
					:key="section.name"
					class="grid gap-4"
					:class="`grid-cols-${section.columns}`"
				>
					<div v-for="field in section.fields" :key="field.name">
						<div
							v-if="field.fieldtype === 'Date'"
							class="text-gray-600 h-1.5 text-xs"
						>
							{{ field.label }}
							<DatePicker
								class="mt-1.5"
								v-if="field.fieldtype === 'Date'"
								v-model="followup_details[field.fieldname]"
								:label="field.label || field.fieldname"
								:name="field.fieldname"
								:required="field.required"
								:format="'DD-MM-YYYY'"
							/>
						</div>
						<FormControl
							v-else
							v-model="followup_details[field.fieldname]"
							:label="field.label || field.fieldname"
							:type="getInputType(field)"
							:name="field.fieldname"
							:options="field.options"
						/>
					</div>
				</div>
				<div>
					<Button
						class="w-full"
						variant="solid"
						label="Update Followup Details"
						@click="updateFollowup.submit()"
					/>
				</div>
			</div>
		</template>
	</Dialog>
</template>
<script setup>
import { createResource, Dialog, FormControl, DatePicker } from 'frappe-ui';
import { computed, reactive, ref } from 'vue';
import { getTeam } from '../../data/team';

const props = defineProps({
	id: {
		type: String,
	},
	leadId: {
		type: String,
	},
});
const show = defineModel();
const followup_details = reactive({
	followup_date: '',
	followup_by: '',
	communication_type: '',
	spoke_to: '',
	designation: '',
	discussion: '',
});

createResource({
	url: 'press.api.partner.fetch_followup_details',
	auto: true,
	makeParams: () => {
		return { id: props.id, lead: props.leadId };
	},
	onSuccess: (data) => {
		if (!data) return '';
		let res = data[0];
		Object.assign(followup_details, {
			followup_date: new Date(res.date).toISOString() || '',
			followup_by: res.followup_by || '',
			communication_type: res.communication_type || '',
			spoke_to: res.spoke_to || '',
			designation: res.designation || '',
			discussion: res.discussion || '',
		});
	},
});

const updateFollowup = createResource({
	url: 'press.api.partner.update_followup_details',
	makeParams: () => {
		return {
			id: props.id || '',
			lead: props.leadId,
			followup_details: followup_details,
		};
	},
	onSuccess: () => {
		show.value = false;
		window.location.reload();
	},
});

const _communicationTypes = [
	'Email',
	'Phone call',
	'Onsite visit',
	'WhatsApp',
	'Telecon',
	'QFC',
	'Demo',
	'DC',
	'Online session',
];
const communicationTypes = computed(() => {
	return _communicationTypes.map((type) => ({
		label: type,
		value: type,
	}));
});

const team = getTeam();
const members = ref([]);
team.getTeamMembers.submit().then((data) => {
	members.value = data.map((member) => ({
		label: member.first_name + ' ' + member.last_name,
		value: member.name,
	}));
});

const sections = computed(() => {
	return [
		{
			name: 'Followup Details',
			columns: 2,
			fields: [
				{
					fieldtype: 'Date',
					label: 'Followup Date',
					fieldname: 'followup_date',
				},
				{
					fieldtype: 'Select',
					label: 'Followup By',
					fieldname: 'followup_by',
					options: members.value,
				},
			],
		},
		{
			name: 'Communication Type',
			columns: 1,
			fields: [
				{
					fieldtype: 'Select',
					label: 'Communication Type',
					fieldname: 'communication_type',
					options: communicationTypes.value,
				},
			],
		},
		{
			name: 'Client Details',
			columns: 2,
			fields: [
				{
					fieldtype: 'Data',
					label: 'Spoke To',
					fieldname: 'spoke_to',
				},
				{
					fieldtype: 'Data',
					label: 'Designation',
					fieldname: 'designation',
				},
			],
		},
		{
			name: 'Notes',
			columns: 1,
			fields: [
				{
					fieldtype: 'Text',
					label: 'Discussion Notes',
					fieldname: 'discussion',
				},
			],
		},
	];
});

function getInputType(field) {
	return {
		Data: 'text',
		Int: 'number',
		Select: 'select',
		Check: 'checkbox',
		Password: 'password',
		Text: 'textarea',
		Date: 'date',
	}[field.fieldtype || 'Data'];
}
</script>
