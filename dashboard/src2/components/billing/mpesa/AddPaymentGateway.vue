<template>
	<Dialog :options="{ title: 'Add Payment Gateway', size: 'lg' }">
		<template #body-content>
			<div class="flex flex-col gap-4">
				<FormControl
					label="Gateway Name"
					v-model="payment_gateway_details.gateway"
					name="gateway_name"
					type="text"
					placeholder="Enter Gateway Name"
				/>
				<!-- <FormControl
        label="Gateway Setting"
        v-model="payment_gateway_details.gateway_settings"
        name="gateway_setting"
        class="mb-5"
        type="select"
        :options="payment_gateway_details.gateway_options"
				/>
        
				<FormControl
        label="Gateway Controller"
        v-model="controllerInput"
        name="gateway_controller"
        class="mb-5"
        type="select"
        :options="controllerOptions"
				/> -->

				<FormControl
					label="Enter endpoint URL"
					v-model="payment_gateway_details.url"
					name="url"
					type="text"
					placeholder="https://xyz.com/api/method/<endpoint>"
				/>
				<div class="flex gap-4">
					<FormControl
						label="API Key"
						v-model="payment_gateway_details.api_key"
						name="api_key"
						type="text"
						placeholder="Enter API Key"
					/>

					<FormControl
						label="API Secret"
						v-model="payment_gateway_details.api_secret"
						name="api_secret"
						type="text"
						placeholder="Enter API Secret"
					/>
				</div>

				<div class="flex gap-4">
					<FormControl
						label="Currency"
						v-model="payment_gateway_details.currency"
						name="currency"
						type="text"
						placeholder="e.g KES"
					/>
					<FormControl
						label="Taxes and Charges(%)"
						v-model="payment_gateway_details.taxes_and_charges"
						name="taxes_and_charges"
						type="text"
						placeholder="Enter Taxes and Charges"
					/>
				</div>
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
			payment_gateway_details: {
				currency: 'KES',
				gateway_name: '',
				gateway_setting: 'Payment Gateway',
				gateway_controller: '',
				url: '',
				api_key: '',
				api_secret: '',
				taxes_and_charges: '',
			},
			integrationLogo: null,
		};
	},
	resources: {
		getPaymentGatewayDetails() {
			return {
				url: 'press.api.regional_payments.mpesa.utils.get_payment_gateway_details',
				onSuccess(data) {
					this.payment_gateway_details = data;
				},
				auto: true,
			};
		},
		createPaymentGatewaySettings() {
			return {
				url: 'press.api.regional_payments.mpesa.utils.update_payment_gateway_settings',
				makeParams() {
					return {
						gateway_details: this.payment_gateway_details,
					};
				},
				validate() {
					let fields = Object.values(this.payment_gateway_details);
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
		fetchGatewayControllers() {
			return {
				url: 'press.api.regional_payments.mpesa.utils.get_gateway_controller',
				method: 'GET',
				auto: true,
				onSuccess: (response) => {
					this.payment_gateway_details.gateway_controller = response;
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
