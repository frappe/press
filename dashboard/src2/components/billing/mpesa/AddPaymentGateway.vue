<template>
	<Dialog :options="{ title: 'Add Payment Gateway', size: 'lg' }">
		<template #body-content>
			<div class="grid grid-cols-2 gap-4">
				<FormControl
					label="Currency"
					:options="currencyOptions"
					v-model="currencyInput"
					name="currency"
					autocomplete="off"
					class="mb-5"
					type="select"
					placeholder="Choose Currency"
					required
				/>

				<FormControl
					label="Gateway Name"
					v-model="gatewayName"
					name="gateway_name"
					autocomplete="off"
					class="mb-5"
					type="text"
					placeholder="Enter Gateway Name"
					required
				/>

				<FormControl
					label="Gateway Setting"
					v-model="gatewayInput"
					name="gateway_setting"
					class="mb-5"
					type="select"
					:options="gatewayOptions"
					required
				/>

				<FormControl
					label="Gateway Controller"
					v-model="controllerInput"
					name="gateway_controller"
					class="mb-5"
					type="select"
					:options="controllerOptions"
					required
				/>

				<FormControl
					label="Enter endpoint URL"
					v-model="URL"
					name="url"
					autocomplete="off"
					class="mb-5"
					type="text"
					placeholder="https://xyz.com/api/method/<endpoint>"
					required
				/>

				<FormControl
					label="API Key"
					v-model="apiKey"
					name="api_key"
					autocomplete="off"
					class="mb-5"
					type="text"
					placeholder="Enter API Key"
					required
				/>

				<FormControl
					label="API Secret"
					v-model="apiSecret"
					name="api_secret"
					autocomplete="off"
					class="mb-5"
					type="text"
					placeholder="Enter API Secret"
					required
				/>

				<FormControl
					label="Taxes and Charges(%)"
					v-model="taxesAndCharges"
					name="taxes_and_charges"
					autocomplete="off"
					class="mb-5"
					type="text"
					placeholder="Enter Taxes and Charges"
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
			currencyOptions: ['KES', 'USD'],
			currencyInput: '',
			gatewayName: '',
			integrationLogo: null,
			gatewayOptions: ['Payment Gateway'],
			gatewayInput: '',
			controllerOptions: [],
			controllerInput: '',
			URL: '',
			apiKey: '',
			apiSecret: '',
			taxesAndCharges: '',
		};
	},
	resources: {
		createPaymentGatewaySettings() {
			return {
				url: 'press.api.regional_payments.mpesa.utils.create_payment_gateway_settings',
				params: {
					currency: this.currencyInput,
					gateway_name: this.gatewayName,
					gateway_setting: this.gatewayInput,
					gateway_controller: this.controllerInput,
					url: this.URL,
					api_key: this.apiKey,
					api_secret: this.apiSecret,
					taxes_and_charges: this.taxesAndCharges,
				},
				validate() {
					const missingFields = [];
					if (!this.currencyInput) missingFields.push('Currency');
					if (!this.gatewayName) missingFields.push('Gateway Name');
					if (!this.gatewayInput) missingFields.push('Gateway Setting');
					if (!this.controllerInput) missingFields.push('Gateway Controller');
					if (!this.URL) missingFields.push('Your site URL');
					if (!this.apiKey) missingFields.push('API Key');
					if (!this.apiSecret) missingFields.push('API Secret');
					if (missingFields.length > 0) {
						return `The following fields are missing: ${missingFields.join(', ')}`;
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
		fetchGatewayControllers(gatewaySetting) {
			return {
				url: 'press.api.regional_payments.mpesa.utils.get_gateway_controllers',
				method: 'GET',
				params: {
					gateway_setting: gatewaySetting,
				},
				onSuccess: (response) => {
					if (Array.isArray(response)) {
						this.controllerOptions = response;
					} else {
						this.$toast.error('No Controllers found');
					}
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
		gatewayInput: function () {
			this.$resources.fetchGatewayControllers.submit({
				gateway_setting: this.gatewayInput,
			});
		},
		integrationLogo: function () {
			this.handleFileUpload();
		},
	},
};
</script>
