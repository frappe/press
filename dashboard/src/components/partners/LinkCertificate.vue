<template>
	<div>
		<Dialog
			:show="show"
			v-model="show"
			:options="{ title: 'Link Certificate' }"
		>
			<template #body-content>
				<p class="pb-3 text-p-base">Enter the details to link a certificate.</p>
				<FormControl
					class="py-2"
					name="certificate_type"
					type="select"
					:options="courseTypes"
					label="Certificate Type"
					v-model="certificateType"
					@change="emailChange"
				/>
				<FormControl
					class="pt-2"
					name="user_email"
					type="text"
					label="User Email"
					v-model="userEmail"
					@input="emailChange"
				/>
				<div class="mt-2">
					<div v-if="certExist" class="text-sm text-green-600" role="alert">
						Found {{ certCount }} certificates with email {{ userEmail }} of
						{{
							courseTypes.find((course) => course.value === certificateType)
								?.label
						}}
						type.
					</div>
				</div>

				<div class="pt-4">
					<Button
						class="w-full"
						variant="solid"
						:loading="linkCertificate.loading"
						label="Link Certificate"
						@click="linkCertificate.submit()"
					/>
				</div>
			</template>
		</Dialog>
	</div>
</template>

<script setup>
import { defineEmits, ref } from 'vue';
import { createResource, frappeRequest, debounce } from 'frappe-ui';
import { toast } from 'vue-sonner';

const courseTypes = [
	{ label: 'Framework', value: 'frappe-developer-certification' },
	{ label: 'ERPNext', value: 'erpnext-distribution' },
];
const show = ref(true);

const userEmail = ref('');
const certificateType = ref('');
const linkCertificate = createResource({
	url: 'press.api.partner.send_link_certificate_request',
	makeParams: () => {
		return {
			user_email: userEmail.value,
			certificate_type: certificateType.value,
		};
	},
	validate: () => {
		if (!userEmail.value || !certificateType.value) {
			throw new Error('Please select a member and certificate type');
		}
	},
	onSuccess: () => {
		show.value = false;
		emit('success');
		toast.success('Email has been sent to the user for linking certificate.');
	},
	onError: (error) => {
		console.error(error);
	},
});

const certCount = ref(0);
const certExist = ref(false);
const emailChange = debounce(async () => {
	if (!userEmail.value) return;
	let response = await frappeRequest({
		url: 'press.api.partner.check_certificate_exists',
		params: {
			email: userEmail.value,
			type: certificateType.value,
		},
	});
	if (response > 0) {
		certCount.value = response;
		certExist.value = true;
	}
}, 500);

const emit = defineEmits(['success']);
</script>
