<template>
	<Dialog :options="{ title: 'Add M-Pesa Credentials', size: 'xl' }">
		<template #body-content>
			<div class="grid grid-cols-2 gap-5">
				<FormControl
					label="Mpesa Setup ID"
					v-model="mpesaSetupDetails.mpesa_setup_id"
					name="mpesa_setup_id"
					class="mb-3"
					type="text"
					placeholder="Test Mpesa"
				/>

				<FormControl
					label="Consumer Key"
					v-model="mpesaSetupDetails.consumer_key"
					name="consumer_key"
					class="mb-3"
					type="text"
					placeholder="Enter Consumer Key"
				/>

				<FormControl
					label="Consumer Secret"
					v-model="mpesaSetupDetails.consumer_secret"
					name="consumer_secret"
					class="mb-3"
					type="text"
					placeholder="Enter Consumer Secret"
				/>

				<FormControl
					label="Pass Key"
					v-model="mpesaSetupDetails.pass_key"
					name="pass_key"
					class="mb-3"
					type="text"
					placeholder="Enter Pass Key"
				/>

				<FormControl
					label="Business Short Code"
					v-model="mpesaSetupDetails.short_code"
					name="short_code"
					class="mb-3"
					type="text"
					placeholder="Enter Short Code"
				/>

				<FormControl
					label="Initiator Name"
					v-model="mpesaSetupDetails.initiator_name"
					name="initiator_name"
					class="mb-3"
					type="text"
					placeholder="e.g John Doe"
				/>

				<FormControl
					label="Security Credential"
					v-model="mpesaSetupDetails.security_credential"
					name="security_credential"
					class="mb-3"
					type="text"
					placeholder="Enter Security Credential"
				/>

				<FormControl
					label="Till Number"
					v-model="mpesaSetupDetails.till_number"
					name="till_number"
					class="mb-3"
					type="text"
					placeholder="1234567"
				/>

				<!-- <div class="flex items-center">
					<input v-model="sandBox" type="checkbox" class="mr-2" />
					<label class="text-sm font-medium text-gray-700">Sandbox Mode</label>
				</div> -->
				<ErrorMessage class="mt-2" :message="errorMessage" />
			</div>

			<div class="mt-4 flex w-full bg-red-300 items-center justify-center">
				<Button
					@click="saveMpesaCredentials"
					variant="solid"
					class="justify-center w-full"
				>
					Save
				</Button>
			</div>
		</template>
	</Dialog>
</template>

<script>
import { toast } from 'vue-sonner';
import { DashboardError } from '../../../utils/error';
import { ErrorMessage } from 'frappe-ui';
export default {
	name: 'AddMpesaCredentials',
	data() {
		return {
			mpesaSetupDetails: {
				consumer_key: '',
				mpesa_setup_id: '',
				consumer_secret: '',
				pass_key: '',
				short_code: '',
				initiator_name: '',
				security_credential: '',
				till_number: '',
				// sandBox: false,
			},
			errorMessage: '',
		};
	},
	resources: {
		createMpesaSetup() {
			return {
				url: 'press.api.regional_payments.mpesa.utils.update_mpesa_setup',
				makeParams() {
					return {
						mpesa_details: this.mpesaSetupDetails,
					};
				},
				validate() {
					let fields = Object.values(this.mpesaSetupDetails);
					if (fields.includes('')) {
						this.errorMessage = 'Please fill required values';
						return 'Please fill required values';
						// throw new DashboardError('Please fill required values');
					}
				},
				onSuccess(data) {
					if (data) {
						toast.success('M-Pesa credentials saved', data);
					} else {
						toast.error('Error saving M-Pesa credentials');
					}
					this.$emit('closeDialog');
				},
			};
		},
		fetchMpesaSetup() {
			return {
				url: 'press.api.regional_payments.mpesa.utils.fetch_mpesa_setup',
				onSuccess(data) {
					Object.assign(this.mpesaSetupDetails, {
						mpesa_setup_id: data.mpesa_setup_id,
						consumer_key: data.consumer_key,
						consumer_secret: data.consumer_secret,
						security_credential: data.security_credential,
						pass_key: data.pass_key,
						short_code: data.business_shortcode,
						till_number: data.till_number,
						initiator_name: data.initiator_name,
					});
				},
				auto: true,
			};
		},
	},
	methods: {
		saveMpesaCredentials() {
			this.$resources.createMpesaSetup.submit();
		},
	},
};
</script>
