<template>
	<div>
		<Dialog
			:show="show"
			v-model="show"
			:options="{ title: 'Apply for Certification' }"
		>
			<template #body-content>
				<p class="pb-3 text-p-base">
					Enter the details to apply for a certificate.
				</p>
				<FormControl
					class="py-2"
					name="certificate_type"
					type="select"
					:options="courseTypes"
					label="Certificate Type"
					v-model="certificateType"
				/>
				<FormControl
					class="pt-2"
					name="member_name"
					type="select"
					:options="memberList"
					label="Member Name"
					v-model="userName"
				/>

				<div class="pt-4">
					<Button
						class="w-full"
						variant="solid"
						label="Apply for Certificate"
						@click="applyForCertificate.submit()"
					/>
				</div>
			</template>
		</Dialog>
	</div>
</template>

<script setup>
import { defineEmits, onMounted, ref } from 'vue';
import { createResource } from 'frappe-ui';
import { getTeam } from '../../data/team';

const courseTypes = [
	{ label: 'Framework', value: 'frappe-developer-certification' },
	{ label: 'ERPNext', value: 'erpnext-distribution' },
];
const show = ref(true);

const team = getTeam();
const memberList = ref([]);
const getMembers = async () => {
	let members = await team.getTeamMembers.submit();
	memberList.value = members.map((member) => {
		return { label: member.full_name, value: member.name };
	});
};
onMounted(() => {
	getMembers();
});

const userName = ref('');
const certificateType = ref('');
const applyForCertificate = createResource({
	url: 'press.api.partner.apply_for_certificate',
	makeParams: () => {
		return {
			member_name: userName.value,
			certificate_type: certificateType.value,
		};
	},
	validate: () => {
		if (!userName.value || !certificateType.value) {
			throw new Error('Please select a member and certificate type');
		}
	},
	onSuccess: () => {
		show.value = false;
		emit('success');
	},
	onError: (error) => {
		console.error(error);
	},
});

const emit = defineEmits(['success']);
</script>
