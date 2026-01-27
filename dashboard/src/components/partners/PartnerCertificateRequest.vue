<template>
	<div>
		<Dialog
			:show="show"
			v-model="show"
			:options="{ title: 'Apply for Certification' }"
		>
			<template #body-content>
				<div v-if="!showMessage">
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

					<div class="pt-4 pb-3">
						<Button
							class="w-full"
							variant="solid"
							label="Apply for Certificate"
							@click="handleApplyForCertificate()"
						/>
					</div>
					<ErrorMessage :message="errorMessage" />
				</div>
				<div v-else>
					<p class="text-p-base">
						You have used both of your free certifications. Please navigate to
						<a :href="batch_link" target="_blank" class="underline">
							this batch
						</a>
						and complete the billing process to enroll in the paid batch.
					</p>
				</div>
			</template>
		</Dialog>
	</div>
</template>

<script setup>
import { defineEmits, onMounted, ref } from 'vue';
import { createResource } from 'frappe-ui';
import { getTeam } from '../../data/team';
import { toast } from 'vue-sonner';

const courseTypes = [
	{ label: 'Framework', value: 'frappe-developer-certification' },
	{ label: 'ERPNext', value: 'erpnext-distribution' },
];
const show = ref(true);
const errorMessage = ref('');

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
	onSuccess: () => {
		show.value = false;
		toast.success('Certificate application submitted successfully.');
		emit('success');
	},
	onError: (error) => {
		errorMessage.value = 'Certificate Request already exists for this member.';
	},
});

const showMessage = ref(false);

const checkCertification = createResource({
	url: 'press.api.partner.can_apply_for_certificate',
	onSuccess: (data) => {
		showMessage.value = !data;
	},
});

let batch_link = ref('');
async function handleApplyForCertificate() {
	if (!userName.value || !certificateType.value) {
		toast.error('Please select a member and certificate type');
		return;
	}

	try {
		await checkCertification.submit();
		if (showMessage.value) {
			batch_link.value = `https://school.frappe.io/lms/billing/certificate/${certificateType.value}`;
			throw new Error(
				'You are not eligible for a free certification at this time.',
			);
		}
		await applyForCertificate.submit();
	} catch (error) {
		console.error(error);
		toast.error(error.message || 'An unexpected error occurred.');
	}
}

const emit = defineEmits(['success']);
</script>
