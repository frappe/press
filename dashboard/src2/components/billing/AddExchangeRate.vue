<template>
	<Dialog :options="{ title: 'Add Currency Exchange', size: 'lg' }">
		<template #body-content>
			<div class="grid grid-cols-2 gap-4">
				<FormControl
					label="From Currency"
					v-model="fromCurrency"
					variant="subtle"
					:options="['USD']"
					name="from_currency"
					type="select"
					class="mb-5"
				/>

				<FormControl
					label="To Currency"
					v-model="toCurrency"
					name="to_currency"
					variant="subtle"
					:options="['KES']"
					type="select"
					class="mb-5"
				/>

				<FormControl
					label="Exchange Rate"
					v-model="exchangeRate"
					name="exchange_rate"
					class="mb-5"
					type="number"
					required
				/>
			</div>

			<div class="mt-4 flex w-full items-center justify-center">
				<Button
					@click="saveExchangeRate"
					class="justify-center w-full"
					variant="solid"
					type="primary"
					>Add Currency Exchange</Button
				>
			</div>
		</template>
		<ErrorMessage class="mt-2" :message="ErrorMessage" />
	</Dialog>
</template>

<script>
import { toast } from 'vue-sonner';
import { FormControl, ErrorMessage } from 'frappe-ui';

export default {
	name: 'AddExchangeRate',
	data() {
		return {
			fromCurrency: 'KES',
			toCurrency: 'USD',
			exchangeRate: '',
		};
	},

	resources: {
		addCurrencyExchange() {
			return {
				url: 'press.api.regional_payments.mpesa.utils.create_exchange_rate',
				params: {
					from_currency: this.fromCurrency,
					to_currency: this.toCurrency,
					exchange_rate: this.exchangeRate,
				},
				validate() {
					if (!this.fromCurrency || !this.toCurrency || !this.exchangeRate) {
						toast.error('All fields are required');
						return false;
					}
				},
				async onSuccess() {
					if (data) {
						toast.success('Currency Exchange Added Successfully');
						this.$emit('close');
					} else {
						toast.error('Failed to add currency exchange');
					}
				},
			};
		},
	},

	methods: {
		async saveExchangeRate() {
			try {
				const response = await this.$resources.addCurrencyExchange.submit();
				if (response) {
					this.$toast.success('Currency Exchange Added Successfully');
					this.fromCurrency = '';
					this.toCurrency = '';
					this.exchangeRate = '';
				}
				this.$emit('closeDialog');
			} catch (error) {
				console.log(error);
				this.$toast.error(`Error adding currency exchange: ${error.message}`);
			}
		},
	},
};
</script>
