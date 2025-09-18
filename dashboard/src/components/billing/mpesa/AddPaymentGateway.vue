<template>
	<Dialog :options="{ title: 'Add Payment Gateway', size: 'lg' }">
		<template #body-content>
			<div class="flex flex-col gap-4">
				<FormControl
					label="Gateway Name"
					v-model="paymentGatewayDetails.gateway_name"
					name="gateway_name"
					type="text"
					placeholder="Enter Gateway Name"
				/>
				<FormControl
					label="Endpoint URL"
					v-model="paymentGatewayDetails.url"
					name="url"
					type="text"
					placeholder="https://xyz.com/api/method/<endpoint>"
				/>
				<div class="flex gap-4">
					<FormControl
						label="API Key"
						v-model="paymentGatewayDetails.api_key"
						name="api_key"
						type="text"
						placeholder="Enter API Key"
					/>

					<FormControl
						label="API Secret"
						v-model="paymentGatewayDetails.api_secret"
						name="api_secret"
						type="text"
						placeholder="Enter API Secret"
					/>
				</div>

				<div class="flex gap-4">
					<FormControl
						label="Currency"
						v-model="paymentGatewayDetails.currency"
						name="currency"
						type="text"
						placeholder="e.g KES"
					/>
					<FormControl
						label="Taxes and Charges(%)"
						v-model="paymentGatewayDetails.taxes_and_charges"
						name="taxes_and_charges"
						type="text"
						placeholder="Enter Taxes and Charges"
					/>
				</div>
				<FormControl
					label="Print Format"
					v-model="paymentGatewayDetails.print_format"
					name="print_format"
					type="text"
					placeholder="Default"
				/>
			</div>

			<div class="mt-4 flex w-full bg-red-300 items-center justify-center">
				<Button
					@click="savePaymentGateway"
					variant="solid"
					class="justify-center w-full font-bold"
					>Save</Button
				>
			</div>
		</template>
	</Dialog>
</template>

<script>
import { toast } from 'vue-sonner';
export default {
	name: 'AddPaymentGateway',
	data() {
		return {
			paymentGatewayDetails: {
				currency: 'KES',
				gateway_name: '',
				gateway_setting: 'Mpesa Setup',
				gateway_controller: '',
				url: '',
				api_key: '',
				api_secret: '',
				taxes_and_charges: '',
				print_format: '',
			},
			integrationLogo: null,
		};
	},
	resources: {
		getPaymentGatewayDetails() {
			return {
				url: 'press.api.regional_payments.mpesa.utils.get_payment_gateway_details',
				onSuccess(data) {
					Object.assign(this.paymentGatewayDetails, {
						currency: data.currency,
						gateway_name: data.gateway_name,
						url: data.url,
						api_key: data.api_key,
						api_secret: data.api_secret,
						taxes_and_charges: data.taxes_and_charges,
						print_format: data.print_format,
					});
				},
				auto: true,
			};
		},
		createPaymentGatewaySettings() {
			return {
				url: 'press.api.regional_payments.mpesa.utils.update_payment_gateway_settings',
				makeParams() {
					return {
						gateway_details: this.paymentGatewayDetails,
					};
				},
				validate() {
					let fields = Object.values(this.paymentGatewayDetails);
					if (fields.includes('')) {
						this.errorMessage = 'Please fill required values';
						return 'Please fill required values';
						// throw new DashboardError('Please fill required values');
					}
				},
				async onSuccess(data) {
					if (data) {
						toast.success('Payment Gateway settings saved', data);
					} else {
						toast.error('Error saving Payment Gateway settings');
					}
				},
			};
		},
		fetchGatewayController() {
			return {
				url: 'press.api.regional_payments.mpesa.utils.get_gateway_controller',
				method: 'GET',
				auto: true,
				onSuccess: (res) => {
					Object.assign(this.paymentGatewayDetails, {
						gateway_controller: res,
					});
				},
			};
		},
	},
	methods: {
		handleFileUpload(event) {
			this.integrationLogo = event.target.files[0];
		},

		async savePaymentGateway() {
			try {
				await this.$resources.createPaymentGatewaySettings.submit();
				this.$emit('closeDialog');
			} catch (error) {
				this.$toast.error(
					`Error saving Payment Gateway settings: ${error.message}`,
				);
			}
		},
	},
	watch: {
		integrationLogo: function () {
			this.handleFileUpload();
		},
	},
};
</script>
