<template>
	<Dialog :options="{ title: 'Add M-Pesa Credentials', size: 'lg' }">
		<template #body-content>
			<div class="grid grid-cols-2 gap-4">
				<FormControl
					label="Mpesa Setup ID"
					v-model="mpesaSetupId"
					name="mpesa_setup_id"
					autocomplete="off"
					class="mb-5"
					type="text"
					placeholder="Enter Mpesa Setup ID"
					required
				/>

				<FormControl
					label="Consumer Key"
					v-model="consumerKey"
					name="consumer_key"
					autocomplete="off"
					class="mb-5"
					type="text"
					placeholder="Enter Consumer Key"
					required
				/>

				<FormControl
					label="Consumer Secret"
					v-model="consumerSecret"
					name="consumer_secret"
					autocomplete="off"
					class="mb-5"
					type="text"
					placeholder="Enter Consumer Secret"
					required
				/>

				<FormControl
					label="Pass Key"
					v-model="passKey"
					name="pass_key"
					autocomplete="off"
					class="mb-5"
					type="text"
					placeholder="Enter Pass Key"
					required
				/>

				<FormControl
					label="Short Code"
					v-model="shortCode"
					name="short_code"
					autocomplete="off"
					class="mb-5"
					type="text"
					placeholder="Enter Short Code"
					required
				/>

				<FormControl
					label="Initiator Name"
					v-model="initiatorName"
					name="initiator_name"
					autocomplete="off"
					class="mb-5"
					type="text"
					placeholder="Enter Initiator Name"
					required
				/>

				<FormControl
					label="Security Credential"
					v-model="securityCredential"
					name="security_credential"
					autocomplete="off"
					class="mb-5"
					type="text"
					placeholder="Enter Security Credential"
					required
				/>

				<FormControl
					label="Till Number"
					v-model="tillNumber"
					name="till_number"
					autocomplete="off"
					class="mb-5"
					type="text"
					placeholder="Enter Till Number"
					required
				/>

				<!-- <div class="flex items-center">
					<input v-model="sandBox" type="checkbox" class="mr-2" />
					<label class="text-sm font-medium text-gray-700">Sandbox Mode</label>
				</div> -->
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
export default {
	name: 'AddMpesaCredentials',
	data() {
		return {
			consumerKey: '',
			mpesaSetupId: '',
			consumerSecret: '',
			passKey: '',
			shortCode: '',
			initiatorName: '',
			securityCredential: '',
			tillNumber: '',
			apiType: '',
			// sandBox: false,
		};
	},
	resources: {
		createMpesaSetup() {
			return {
				url: 'press.api.regional_payments.mpesa.utils.create_mpesa_setup',
				params: {
					mpesa_setup_id: this.mpesaSetupId,
					consumer_key: this.consumerKey,
					consumer_secret: this.consumerSecret,
					pass_key: this.passKey,
					short_code: this.shortCode,
					initiator_name: this.initiatorName,
					security_credential: this.securityCredential,
					till_number: this.tillNumber,
					// sandbox: this.sandBox,
				},
				validate() {
					if (
						!this.mpesaSetupId ||
						!this.consumerKey ||
						!this.consumerSecret ||
						!this.passKey ||
						!this.shortCode ||
						!this.initiatorName ||
						!this.securityCredential
					) {
						return 'All fields are required';
					}
				},
				onSuccess(data) {
					if (data) {
						toast.success('M-Pesa credentials saved', data);
					} else {
						toast.error('Error saving M-Pesa credentials');
					}
				},
			};
		},
		fetchMpesaSetup() {
			return {
				url: 'press.api.regional_payments.mpesa.utils.fetch_mpesa_setup',
				onSuccess(data) {
					console.log('data', data);
					this.mpesaSetupId = data.mpesa_setup_id;
					this.consumerKey = data.consumer_key;
					this.consumerSecret = data.consumer_secret;
					this.securityCredential = data.security_credential;
					this.passKey = data.pass_key;
					this.shortCode = data.business_shortcode;
					this.tillNumber = data.till_number;
					this.initiatorName = data.initiator_name;
					this.apiType = data.api_type;
				},
				auto: true,
			};
		},
	},
	methods: {
		saveMpesaCredentials() {
			this.$resources.createMpesaSetup.submit();
			this.$emit('closeDialog');
		},
	},
};
</script>
